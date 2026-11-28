import json
import math
import os
from pathlib import Path
import random
import re
from dataclasses import dataclass
from typing import Optional

try:
    from .config import disease_chance_per_turn
except ImportError:
    from config import disease_chance_per_turn


IMMUNE_SYSTEM_LENGTH = 50
DISEASES_DIR = Path(__file__).resolve().parent / "diseases"


def contagiousness_from_r0(r0_estimate):
    """Approximate a per-contact probability from an R0 value."""
    if (isinstance(r0_estimate, bool)
            or not isinstance(r0_estimate, (int, float))
            or not math.isfinite(r0_estimate)
            or r0_estimate < 1):
        raise ValueError("R0 must be a finite number greater than or equal to 1")
    return 1 - 1 / r0_estimate


@dataclass(frozen=True)
class Disease:
    name: str
    pattern: str
    contagiousness: float
    r0_estimate: Optional[float] = None
    health_damage_per_turn: float = 1.0

    def __post_init__(self):
        if (isinstance(self.contagiousness, bool)
                or not isinstance(self.contagiousness, (int, float))
                or not math.isfinite(self.contagiousness)
                or not 0 <= self.contagiousness <= 1):
            raise ValueError("Contagiousness must be a number between 0 and 1")
        if self.r0_estimate is not None:
            contagiousness_from_r0(self.r0_estimate)
        if (isinstance(self.health_damage_per_turn, bool)
                or not isinstance(self.health_damage_per_turn, (int, float))
                or not math.isfinite(self.health_damage_per_turn)
                or self.health_damage_per_turn < 0):
            raise ValueError("Disease health damage must be a finite non-negative number")


def _load_all_diseases():
    registry = {}
    if not DISEASES_DIR.exists():
        DISEASES_DIR.mkdir(parents=True, exist_ok=True)
    for path in DISEASES_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                d_id = path.stem
                registry[d_id] = Disease(
                    name=data.get("name", d_id.replace("_", " ").title()),
                    pattern=data.get("pattern", ""),
                    contagiousness=data.get("contagiousness", 0.5),
                    r0_estimate=data.get("r0_estimate"),
                    health_damage_per_turn=data.get("health_damage_per_turn", 1.0),
                )
        except Exception as e:
            print(f"Failed to load disease from {path}: {e}")
    return registry


def refresh_diseases():
    """Reload all diseases from disk and update the global registries."""
    global DISEASES, DISEASE_ORDER
    DISEASES.update(_load_all_diseases())
    # Also remove any that were deleted? For now, just update/add.
    new_order = sorted(list(DISEASES.keys()))
    DISEASE_ORDER.clear()
    DISEASE_ORDER.extend(new_order)


DISEASES = _load_all_diseases()
DISEASE_ORDER = sorted(list(DISEASES.keys()))


def register_custom_disease(name, pattern, contagiousness=None, r0_estimate=None,
                            health_damage_per_turn=1.0):
    """Register a new disease pattern at runtime and save to disk."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Disease name is required")
    d_id = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
    if not d_id:
        raise ValueError("Disease name must contain letters or numbers")
    if (not isinstance(pattern, str) or not 1 <= len(pattern) <= IMMUNE_SYSTEM_LENGTH
            or any(bit not in "01" for bit in pattern)):
        raise ValueError("Disease patterns must contain 1 to 50 binary digits")

    if r0_estimate is not None:
        if contagiousness is not None:
            raise ValueError("Provide either contagiousness or R0, not both")
        contagiousness = contagiousness_from_r0(r0_estimate)
    elif contagiousness is None:
        raise ValueError("Provide either contagiousness or R0")

    disease = Disease(name, pattern, contagiousness, r0_estimate,
                      health_damage_per_turn)

    existing = DISEASES.get(d_id)
    if existing is not None:
        if existing == disease:
            return d_id
        if (existing.name != disease.name
                or existing.pattern != disease.pattern
                or existing.contagiousness != disease.contagiousness
                or existing.r0_estimate != disease.r0_estimate):
            raise ValueError("A disease with this name already exists")
        # A config may update damage for an existing custom disease.
    
    # Save to disk
    if not DISEASES_DIR.exists():
        DISEASES_DIR.mkdir(parents=True, exist_ok=True)
    
    path = DISEASES_DIR / f"{d_id}.json"
    data = {
        "name": name,
        "pattern": pattern,
        "contagiousness": contagiousness,
        "health_damage_per_turn": health_damage_per_turn,
    }
    if r0_estimate is not None:
        data["r0_estimate"] = r0_estimate
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    # Refresh the global registry so all modules see the change
    refresh_diseases()
    
    return d_id


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
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= IMMUNE_SYSTEM_LENGTH:
        raise ValueError("Disease patterns must contain between 1 and {} bits".format(IMMUNE_SYSTEM_LENGTH))
    if any(bit not in "01" for bit in pattern):
        raise ValueError("Disease patterns must contain only binary digits")
    if len(pattern) > len(immune_system):
        raise ValueError("Disease pattern cannot exceed the immune system length")

    best_start = 0
    # The agent is only immune if any position matches exactly,
    # otherwise take the position with the fewest differences.
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
                    # Vaccine protection check
                    expiry = target.vaccination_expiry.get(disease_id, 0)
                    if expiry > world_obj.turnNo:
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


def _repair_immune_systems(agents, days_elapsed=1.0):
    for agent in sorted(agents, key=lambda item: item.id):
        disease_id = next((d for d in DISEASE_ORDER if d in agent.diseases), None)

        if disease_id is None:
            # Clear info for agents who aren't sick and don't have pending infections
            if not agent.pending_diseases:
                agent.disease_info.clear()
            continue  # Agent isn't sick, skip to next agent

        if not hasattr(agent, "disease_info"):
            agent.disease_info = {}
        if disease_id not in agent.disease_info:
            agent.disease_info[disease_id] = {
                "active_days": 0.0,
                "repair_progress": 0.0,
                "is_vaccinated": False,
            }

        info = agent.disease_info[disease_id]
        previous_active_days = info.get("active_days", 0.0)
        active_days = previous_active_days + max(0.0, days_elapsed)
        info["active_days"] = active_days
        # The first two days are an incubation/response delay. After that,
        # ordinary repair accrues at half a bit per day; hospital care doubles it.
        eligible_days = max(0.0, active_days - 2.0) - max(
            0.0, previous_active_days - 2.0
        )
        repair_rate = 1.0 if agent.hospitalized_at is not None else 0.5
        repair_budget = info.get("repair_progress", 0.0) + eligible_days * repair_rate

        while repair_budget >= 1.0 and (agent.diseases or agent.pending_diseases):
            # Check all current diseases to see if any have been cured by repairs for others
            recovered = [d for d in agent.diseases if is_immune(agent.immune_system, d)]
            for d in recovered:
                agent.diseases.remove(d)
                print("Agent {} recovered from {}.".format(agent.id, DISEASES[d].name))
            
            # Also check pending diseases
            recovered_pending = [d for d in agent.pending_diseases if is_immune(agent.immune_system, d)]
            for d in recovered_pending:
                agent.pending_diseases.remove(d)
                print("Agent {}'s pending infection of {} was cleared by immunity.".format(agent.id, DISEASES[d].name))

            if not agent.diseases and not agent.pending_diseases:
                break
            
            # Pick a disease to work on (diseases first, then pending)
            disease_id = next((d for d in DISEASE_ORDER if d in agent.diseases), None)
            if disease_id is None:
                disease_id = next((d for d in DISEASE_ORDER if d in agent.pending_diseases), None)
            
            if disease_id is None:
                break
                
            disease = DISEASES[disease_id]
            
            start, mismatches = find_best_match(agent.immune_system, disease.pattern)
            if not mismatches:
                # Should have been caught by the check above
                if disease_id in agent.diseases:
                    agent.diseases.remove(disease_id)
                elif disease_id in agent.pending_diseases:
                    agent.pending_diseases.remove(disease_id)
                continue
            
            # Repair one mismatching bit
            position = start + mismatches[0]
            corrected = list(agent.immune_system)
            corrected[position] = disease.pattern[mismatches[0]]
            agent.immune_system = "".join(corrected)
            repair_budget -= 1
            
            # Check if cured this one
            if is_immune(agent.immune_system, disease_id):
                if disease_id in agent.diseases:
                    agent.diseases.remove(disease_id)
                    print("Agent {} recovered from {}.".format(agent.id, disease.name))
                elif disease_id in agent.pending_diseases:
                    agent.pending_diseases.remove(disease_id)
                    print("Agent {}'s pending infection of {} was cleared by immunity.".format(agent.id, disease.name))
        
        info["repair_progress"] = repair_budget

        # Final check
        recovered = [d for d in agent.diseases if is_immune(agent.immune_system, d)]
        for d in recovered:
            agent.diseases.remove(d)
            print("Agent {} recovered from {}.".format(agent.id, DISEASES[d].name))
        recovered_pending = [d for d in agent.pending_diseases if is_immune(agent.immune_system, d)]
        for d in recovered_pending:
            agent.pending_diseases.remove(d)



def process_disease_turn(agents, world_obj):
    """Resolve contact, introductions, and immune repair in a stable order."""
    ordered = sorted(agents, key=lambda item: item.id)
    neighbors = _contact_neighbors(ordered)
    _spread_diseases(ordered, world_obj, neighbors)
    _introduce_community_cases(ordered, world_obj)
    days_elapsed = getattr(world_obj, "time_step_days", 1.0) if world_obj is not None else 1.0
    _repair_immune_systems(ordered, days_elapsed)


def disease_health_damage(agent, world_obj=None):
    """Return direct health damage from active diseases for this turn."""
    config = getattr(world_obj, "config", {}) if world_obj is not None else {}
    disease_config = config.get("Health & Disease", {}) if isinstance(config, dict) else {}
    configured_damage = disease_config.get("disease_health_damage_per_turn", {})
    damage = 0.0
    for disease_id in agent.diseases:
        disease = DISEASES.get(disease_id)
        if disease is None:
            continue
        amount = (configured_damage.get(disease_id, disease.health_damage_per_turn)
                  if isinstance(configured_damage, dict) else configured_damage)
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError(
                "Health & Disease disease_health_damage_per_turn values must be non-negative numbers"
            )
        damage += amount
    return damage


def disease_hunger_cost(agent):
    """Disease no longer adds to hunger drain; retained for compatibility."""
    return 0
