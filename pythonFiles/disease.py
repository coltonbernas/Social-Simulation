import random
from dataclasses import dataclass

try:
    from .config import disease_chance_per_turn
except ImportError:
    from config import disease_chance_per_turn


IMMUNE_SYSTEM_LENGTH = 50


@dataclass(frozen=True)
class Disease:
    name: str
    pattern: str
    contagiousness: float


DISEASES = {
    "measles": Disease("Measles", "1101010010", 0.9),
    "common_cold": Disease("Common cold", "10101", 0.5),
    "influenza": Disease("Influenza", "01101011", 0.4),
    "covid_19": Disease("COVID-19", "1100101", 0.55),
    "pneumonic_plague": Disease("Pneumonic plague", "001110", 0.25),
}
DISEASE_ORDER = tuple(DISEASES)


def random_immune_system():
    return "".join(random.choice("01") for _ in range(IMMUNE_SYSTEM_LENGTH))


def combine_parent_immune_systems(first, second):
    validate_immune_system(first)
    validate_immune_system(second)
    return "".join(
        first_bit if first_bit == second_bit else random.choice((first_bit, second_bit))
        for first_bit, second_bit in zip(first, second)
    )


def validate_immune_system(immune_system):
    if (not isinstance(immune_system, str)
            or len(immune_system) != IMMUNE_SYSTEM_LENGTH
            or any(bit not in "01" for bit in immune_system)):
        raise ValueError("Immune systems must be 50-character binary strings")


def find_best_match(immune_system, pattern):
    """Return the earliest substring with the fewest differing bits."""
    validate_immune_system(immune_system)
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 10:
        raise ValueError("Disease patterns must contain between 1 and 10 bits")
    if any(bit not in "01" for bit in pattern):
        raise ValueError("Disease patterns must contain only binary digits")
    if len(pattern) > len(immune_system):
        raise ValueError("Disease pattern cannot exceed the immune system length")

    best_start = 0
    best_mismatches = tuple(range(len(pattern)))
    for start in range(len(immune_system) - len(pattern) + 1):
        mismatches = tuple(
            index for index, bit in enumerate(pattern)
            if immune_system[start + index] != bit
        )
        if len(mismatches) < len(best_mismatches):
            best_start, best_mismatches = start, mismatches
            if not mismatches:
                break
    return best_start, best_mismatches


def is_immune(immune_system, disease_id):
    disease = DISEASES[disease_id]
    return not find_best_match(immune_system, disease.pattern)[1]


def disease_name(disease_id):
    return DISEASES[disease_id].name


def disease_pattern(disease_id):
    return DISEASES[disease_id].pattern


def disease_progress(immune_system, disease_id):
    """Describe the closest match as repaired bits remaining / pattern length."""
    disease = DISEASES[disease_id]
    _, mismatches = find_best_match(immune_system, disease.pattern)
    return len(mismatches), len(disease.pattern)


def activate_pending_infections(agents):
    """Make prior-turn exposures active before agents move this turn."""
    for agent in sorted(agents, key=lambda item: item.id):
        for disease_id in DISEASE_ORDER:
            if disease_id not in agent.pending_diseases:
                continue
            agent.pending_diseases.remove(disease_id)
            if not is_immune(agent.immune_system, disease_id):
                agent.diseases.add(disease_id)


def _record_infection(world_obj, agent, disease_id, source_id=None, source=None):
    if world_obj is None:
        return
    event = {
        "turn": world_obj.turnNo + 1,
        "agent_id": agent.id,
        "disease": disease_id,
        "health": agent.health,
    }
    if source_id is None:
        event["source"] = source or "natural"
    else:
        event["source_id"] = source_id
    world_obj.disease_events.append(event)


def introduce_disease(agent, disease_id, world_obj):
    """Queue a user-selected infection, respecting immunity and next-turn onset."""
    if disease_id not in DISEASES:
        raise ValueError("Unknown disease: {}".format(disease_id))
    if (disease_id in agent.diseases
            or disease_id in agent.pending_diseases
            or is_immune(agent.immune_system, disease_id)):
        return False
    agent.pending_diseases.add(disease_id)
    _record_infection(world_obj, agent, disease_id, source="user")
    return True


def _contact_neighbors(agents):
    neighbors = {agent.id: set() for agent in agents}
    ordered = sorted(agents, key=lambda item: item.id)
    for index, first in enumerate(ordered):
        for second in ordered[index + 1:]:
            if (max(abs(first.pos_x - second.pos_x),
                    abs(first.pos_y - second.pos_y)) <= 1):
                neighbors[first.id].add(second.id)
                neighbors[second.id].add(first.id)
    return neighbors


def _introduce_community_cases(agents, world_obj):
    config = getattr(world_obj, "config", {}) if world_obj is not None else {}
    disease_config = config.get("Health & Disease", {}) if isinstance(config, dict) else {}
    chance = disease_config.get(
        "community_case_chance_per_turn",
        disease_config.get("disease_chance_per_turn", disease_chance_per_turn),
    )
    if chance <= 0:
        return

    for agent in sorted(agents, key=lambda item: item.id):
        if agent.diseases or agent.pending_diseases or random.random() >= chance:
            continue
        susceptible_diseases = [
            disease_id for disease_id in DISEASE_ORDER
            if not is_immune(agent.immune_system, disease_id)
        ]
        if not susceptible_diseases:
            continue
        disease_id = random.choice(susceptible_diseases)
        agent.pending_diseases.add(disease_id)
        _record_infection(world_obj, agent, disease_id)


def _spread_diseases(agents, world_obj, neighbors):
    agents_by_id = {agent.id: agent for agent in agents}
    for disease_id in DISEASE_ORDER:
        disease = DISEASES[disease_id]
        exposed = {
            agent.id for agent in agents
            if disease_id in agent.diseases or disease_id in agent.pending_diseases
        }
        wave = {
            agent.id for agent in agents if disease_id in agent.diseases
        }
        while wave:
            next_wave = set()
            for source_id in sorted(wave):
                source = agents_by_id[source_id]
                for target_id in sorted(neighbors[source_id]):
                    if target_id in exposed:
                        continue
                    target = agents_by_id[target_id]
                    if is_immune(target.immune_system, disease_id):
                        continue
                    if random.random() < disease.contagiousness:
                        exposed.add(target_id)
                        target.pending_diseases.add(disease_id)
                        next_wave.add(target_id)
                        _record_infection(world_obj, target, disease_id, source_id)
                        print("Agent {} was exposed to {} by Agent {}; illness begins next turn.".format(
                            target.id, disease.name, source.id
                        ))
            wave = next_wave


def _repair_immune_systems(agents):
    for agent in sorted(agents, key=lambda item: item.id):
        repair_budget = 2 if agent.hospitalized_at is not None else 1
        while repair_budget and agent.diseases:
            for candidate in DISEASE_ORDER:
                if (candidate in agent.diseases
                        and is_immune(agent.immune_system, candidate)):
                    agent.diseases.remove(candidate)
                    print("Agent {} recovered from {}.".format(
                        agent.id, DISEASES[candidate].name
                    ))
            disease_id = next(
                (candidate for candidate in DISEASE_ORDER
                 if candidate in agent.diseases),
                None,
            )
            if disease_id is None:
                break
            disease = DISEASES[disease_id]
            start, mismatches = find_best_match(agent.immune_system, disease.pattern)
            if not mismatches:
                agent.diseases.remove(disease_id)
                print("Agent {} recovered from {}.".format(agent.id, disease.name))
                continue
            position = start + mismatches[0]
            corrected = list(agent.immune_system)
            corrected[position] = disease.pattern[mismatches[0]]
            agent.immune_system = "".join(corrected)
            repair_budget -= 1
            print("Agent {} immune system repaired one bit for {} ({} mismatch(es) remain).".format(
                agent.id, disease.name,
                disease_progress(agent.immune_system, disease_id)[0]
            ))
            if is_immune(agent.immune_system, disease_id):
                agent.diseases.remove(disease_id)
                print("Agent {} recovered from {}.".format(agent.id, disease.name))


def process_disease_turn(agents, world_obj):
    """Resolve contact, introductions, and immune repair in a stable order."""
    ordered = sorted(agents, key=lambda item: item.id)
    neighbors = _contact_neighbors(ordered)
    _spread_diseases(ordered, world_obj, neighbors)
    _introduce_community_cases(ordered, world_obj)
    _repair_immune_systems(ordered)


def disease_hunger_cost(agent):
    """Extra hunger drained per turn, scaled by the lengths of active patterns."""
    return sum(
        len(DISEASES[disease_id].pattern)
        for disease_id in agent.diseases
        if disease_id in DISEASES
    )
