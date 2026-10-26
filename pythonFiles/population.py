import random

try:
    from .agent import Agent
    from .config import agent_count, building_names, grocery_food_cost, grocery_hunger_threshold
except ImportError:
    from agent import Agent
    from config import agent_count, building_names, grocery_food_cost, grocery_hunger_threshold


class Population:
    def __init__(self, world_obj, count=None):
        # Read updated agent count dynamically from world_obj.config if count isn't explicitly passed
        if count is None:
            config = getattr(world_obj, "config", {})
            # Look in nested "Agent & Population" category first, then top-level flat key
            agent_cfg = config.get("Agent & Population", config) if isinstance(config, dict) else {}
            count = agent_cfg.get("agent_count", config.get("agent_count", agent_count))

        self.agents = [Agent(agent_id=i, world_obj=world_obj) for i in range(count)]
        self.all_agents = list(self.agents)
        self.next_agent_id = count

    def birth(self, world_obj):
        """Create and add a newborn agent whose age is exactly 0."""
        newborn = Agent(
            agent_id=self.next_agent_id,
            world_obj=world_obj,
            age=0,
            birth_turn=world_obj.turnNo + 1,
        )
        self.next_agent_id += 1
        self.agents.append(newborn)
        self.all_agents.append(newborn)
        return newborn

    def birth_child(self, world_obj, first_parent, second_parent):
        """Create one child for a dating pair and inherit their ethnic makeup."""
        inherited_percentages = {}
        for parent in (first_parent, second_parent):
            for ethnicity, percentage in parent.ethnicity_percentages.items():
                inherited_percentages[ethnicity] = (
                    inherited_percentages.get(ethnicity, 0.0) + percentage / 2
                )
        inherited_percentages = {
            ethnicity: percentage
            for ethnicity, percentage in inherited_percentages.items()
            if percentage > 0
        }
        if len(inherited_percentages) == 1:
            inherited_ethnicity = next(iter(inherited_percentages))
        else:
            inherited_ethnicity = " / ".join(
                "{}% {}".format(round(percentage, 1), ethnicity)
                for ethnicity, percentage in sorted(inherited_percentages.items())
            )

        newborn = Agent(
            agent_id=self.next_agent_id,
            world_obj=world_obj,
            age=0,
            ethnicity=inherited_ethnicity,
            ethnicity_percentages=inherited_percentages,
            parent_ids=(first_parent.id, second_parent.id),
            birth_turn=world_obj.turnNo + 1,
            religion=random.choice((first_parent.religion, second_parent.religion)),
        )
        self.next_agent_id += 1
        self.agents.append(newborn)
        self.all_agents.append(newborn)
        first_parent.children_ids.add(newborn.id)
        second_parent.children_ids.add(newborn.id)
        world_obj.birth_events.append({
            "turn": world_obj.turnNo + 1,
            "agent_id": newborn.id,
            "parent_ids": (first_parent.id, second_parent.id),
            "parent_names": (first_parent.name, second_parent.name),
            "ethnicity_percentages": dict(inherited_percentages),
            "position": (newborn.pos_x, newborn.pos_y),
            "age": newborn.age,
            "death_age": newborn.death_age,
            "intelligence": newborn.intelligence,
            "willpower": newborn.willpower,
            "personality": newborn.personality_type,
            "gender": newborn.gender,
            "religion": newborn.religion,
        })
        print("Agent {} was born to {} and {}; spawned at ({}, {}); age: {}; "
              "natural death age: {}; intelligence: {}; willpower: {}; "
              "personality: {}; gender: {}; ethnicity: {}; religion: {}.".format(
            newborn.id, first_parent.name, second_parent.name,
            newborn.pos_x, newborn.pos_y, newborn.age, newborn.death_age,
            newborn.intelligence, newborn.willpower, newborn.personality_type,
            newborn.gender, inherited_ethnicity, newborn.religion
        ))
        return newborn

    def share_information(self, first, second, world_obj):
        """Record an in-sight interaction and exchange known empty locations."""
        turn = world_obj.turnNo + 1
        first_locations = tuple(sorted(first.known_empty))
        second_locations = tuple(sorted(second.known_empty))

        first.receive_message(second_locations)
        second.receive_message(first_locations)

        first_last_interaction = first.interaction_last_turn.get(second.id)
        second_last_interaction = second.interaction_last_turn.get(first.id)
        relationship_stage, relationship_points = self._advance_relationship(
            first, second, turn, world_obj
        )
        gift_offers = [
            self._gift_offer(first, second, first_last_interaction, turn, relationship_stage),
            self._gift_offer(second, first, second_last_interaction, turn, relationship_stage),
        ]
        gift_offers = [offer for offer in gift_offers if offer is not None]
        if gift_offers:
            # One interaction produces at most one gift, avoiding both agents
            # immediately returning each other's money.
            giver, receiver, amount, reason = max(
                gift_offers,
                key=lambda offer: (offer[2], offer[0].wealth, -offer[0].id),
            )
            self._transfer_wealth(giver, receiver, amount, reason, turn, world_obj)

        if second.name not in first.interacted_agents:
            first.interacted_agents.append(second.name)
        if first.name not in second.interacted_agents:
            second.interacted_agents.append(first.name)
        first.interaction_last_turn[second.id] = turn
        second.interaction_last_turn[first.id] = turn

        world_obj.communication_events.extend((
            {
                "turn": turn,
                "sender_id": first.id,
                "receiver_id": second.id,
                "sender_name": first.name,
                "receiver_name": second.name,
                "empty_locations": first_locations,
            },
            {
                "turn": turn,
                "sender_id": second.id,
                "receiver_id": first.id,
                "sender_name": second.name,
                "receiver_name": first.name,
                "empty_locations": second_locations,
            },
        ))
        print("{} interacted with {} (relationship: {} points; {}). They exchanged {} and {} known empty location(s).".format(
            first.name, second.name, relationship_points, relationship_stage,
            len(first_locations), len(second_locations)
        ))

        # Close encounters can transmit disease, with risk adjusted for recipient health.
        self._try_transmission(first, second, world_obj)
        self._try_transmission(second, first, world_obj)

    @staticmethod
    def _advance_relationship(first, second, turn, world_obj):
        """Award interaction points and establish friendship or exclusive dating."""
        previous_points = first.relationship_points.get(second.id, 0)
        old_stage = Population._relationship_stage(first, second, previous_points)
        is_parent_child = (
            second.id in first.parent_ids or first.id in second.parent_ids
        )
        points = min(10, previous_points + 5) if is_parent_child else previous_points + 5
        first.relationship_points[second.id] = points
        second.relationship_points[first.id] = points

        can_date_each_other = (
            not is_parent_child
            and
            first.dating_partner_id in (None, second.id)
            and second.dating_partner_id in (None, first.id)
        )
        if points >= 11 and can_date_each_other:
            first.dating_partner_id = second.id
            second.dating_partner_id = first.id
            if first.dating_since_turn is None:
                first.dating_since_turn = turn
            if second.dating_since_turn is None:
                second.dating_since_turn = turn

        stage = Population._relationship_stage(first, second, points)
        event = {
            "turn": turn,
            "first_id": first.id,
            "second_id": second.id,
            "first_name": first.name,
            "second_name": second.name,
            "points": points,
            "stage": stage,
            "stage_changed": stage != old_stage,
        }
        world_obj.relationship_events.append(event)
        if event["stage_changed"]:
            print("{} and {} are now {} ({} relationship points).".format(
                first.name, second.name, stage, points
            ))
        return stage, points

    @staticmethod
    def _relationship_stage(first, second, points):
        if (points >= 11 and first.dating_partner_id == second.id
                and second.dating_partner_id == first.id):
            return "dating"
        if points >= 6:
            return "friends"
        return "no relationship"

    @staticmethod
    def _gift_offer(giver, receiver, previous_interaction_turn, turn, relationship_stage):
        """Return the gift this unstressed agent can afford to offer, if any."""
        if giver.active_stressful_events or relationship_stage not in ("friends", "dating"):
            return None

        if (previous_interaction_turn is not None
                and turn - previous_interaction_turn >= 5):
            amount = 500
            reason = "reconnected after at least 5 turns"
        elif receiver.wealth < 500:
            amount = 250
            reason = "recipient had less than $500"
        else:
            return None

        if giver.wealth < amount:
            return None
        return giver, receiver, amount, reason

    @staticmethod
    def _transfer_wealth(giver, receiver, amount, reason, turn, world_obj):
        """Record and print an affordable gift between two interacting agents."""
        giver.wealth -= amount
        receiver.wealth += amount
        event = {
            "turn": turn,
            "from_id": giver.id,
            "from_name": giver.name,
            "to_id": receiver.id,
            "to_name": receiver.name,
            "amount": amount,
            "reason": reason,
            "giver_wealth": giver.wealth,
            "receiver_wealth": receiver.wealth,
        }
        world_obj.money_transfer_events.append(event)
        print("{} transferred ${:,} to {} ({}). Wealth is now ${:,} and ${:,}.".format(
            giver.name, amount, receiver.name, reason,
            giver.wealth, receiver.wealth
        ))

    @staticmethod
    def _try_transmission(source, target, world_obj):
        if not source.diseases:
            return
        disease = sorted(source.diseases)[0]
        # Pass world_obj so catch_disease can read active UI sliders
        if target.catch_disease(world_obj, disease):
            world_obj.disease_events.append({
                "turn": world_obj.turnNo + 1,
                "source_id": source.id,
                "agent_id": target.id,
                "disease": disease,
                "health": target.health,
            })
            print("Agent {} caught {} passed by Agent {} (health: {}).".format(
                target.id, disease, source.id, target.health
            ))

    def step_agents(self, world_obj):
        # One simulation turn represents one year of aging.
        for agent in list(self.agents):
            if agent.age < agent.death_age:
                agent.age += 1
            if (agent.parent_ids and agent.birth_turn is not None
                    and agent.age == 10):
                if random.random() < 0.20:
                    previous_religion = agent.religion
                    agent.religion = "Unaffiliated"
                    print("Agent {} became unaffiliated at age 10 (previous religion: {}).".format(
                        agent.id, previous_religion
                    ))
            if agent.age >= agent.death_age:
                self._remove_agent(agent, world_obj, "old age")

        self._support_young_children(world_obj)

        # Record sightings after all agents have moved so each pair interacts at
        # most once when they newly enter one another's adjacent sight line.
        agents_by_id = {agent.id: agent for agent in self.agents}
        blocked_pairs = set()
        for agent in self.agents:
            other_agent_id = agent.move(world_obj)
            if other_agent_id is not None:
                blocked_pairs.add(tuple(sorted((agent.id, other_agent_id))))

        current_sightings = {agent.id: set() for agent in self.agents}
        interacted_pairs = set()
        for index, first in enumerate(self.agents):
            for second in self.agents[index + 1:]:
                if max(abs(first.pos_x - second.pos_x), abs(first.pos_y - second.pos_y)) <= 1:
                    pair = (first.id, second.id)
                    current_sightings[first.id].add(second.id)
                    current_sightings[second.id].add(first.id)
                    newly_visible = (
                        second.id not in first.visible_agent_ids
                        and first.id not in second.visible_agent_ids
                    )
                    if newly_visible:
                        self.share_information(first, second, world_obj)
                        interacted_pairs.add(pair)

        # Preserve collision-based disease transmission when the pair was
        # already visible and therefore did not create a new interaction.
        for first_id, second_id in blocked_pairs - interacted_pairs:
            first = agents_by_id.get(first_id)
            second = agents_by_id.get(second_id)
            if first is not None and second is not None:
                self._try_transmission(first, second, world_obj)
                self._try_transmission(second, first, world_obj)

        for agent in self.agents:
            agent.visible_agent_ids = current_sightings[agent.id]
        self._process_births(world_obj)
        for agent in list(self.agents):
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
                continue
            agent.earn_income()
            agent.update_health(world_obj)
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
            else:
                agent.advance_hospital_stay(world_obj)
                agent.advance_school(world_obj)
                agent.advance_house_stay(world_obj)
        world_obj.turnNo +=1

    def _support_young_children(self, world_obj):
        """Transfer grocery money when young children are hungry and parents can cover it."""
        turn = world_obj.turnNo + 1
        for child in self.agents:
            if (not child.parent_ids or child.birth_turn is None
                    or turn - child.birth_turn > 10
                    or child.hunger >= grocery_hunger_threshold):
                continue
            shortfall = max(0, grocery_food_cost - child.wealth)
            parents = [parent for parent in self.agents if parent.id in child.parent_ids]
            if shortfall == 0 or sum(parent.wealth for parent in parents) < shortfall:
                continue
            for parent in sorted(parents, key=lambda item: item.id):
                amount = min(shortfall, parent.wealth)
                if amount <= 0:
                    continue
                self._transfer_wealth(
                    parent, child, amount,
                    "parental grocery loan for Agent {}".format(child.id),
                    turn, world_obj,
                )
                shortfall -= amount
                if shortfall == 0:
                    break

    def _process_births(self, world_obj):
        """Give an eligible dating pair one child after more than five turns."""
        turn = world_obj.turnNo + 1
        agents_by_id = {agent.id: agent for agent in self.agents}
        for first in list(self.agents):
            partner_id = first.dating_partner_id
            if (partner_id is None
                    or first.dating_since_turn is None
                    or turn - first.dating_since_turn <= 5):
                continue
            second = agents_by_id.get(partner_id)
            if (second is None or second.dating_partner_id != first.id
                    or first.children_ids.intersection(second.children_ids)):
                continue
            self.birth_child(world_obj, first, second)

    def _remove_agent(self, agent, world_obj, cause):
        """Remove a dead agent and reopen any job they held."""
        if cause == "zero health":
            cause = agent.last_health_damage_cause or "unknown cause"
        if agent.job is not None:
            world_obj.reopen_job(
                agent.employed_at, agent, reason="died from {}".format(cause)
            )
        if agent.dating_partner_id is not None:
            former_partner = next(
                (other for other in self.agents
                 if other.id == agent.dating_partner_id and other.id != agent.id),
                None,
            )
            if former_partner is not None:
                former_partner.dating_partner_id = None
                former_partner.dating_since_turn = None
                world_obj.relationship_events.append({
                    "turn": world_obj.turnNo + 1,
                    "first_id": agent.id,
                    "second_id": former_partner.id,
                    "first_name": agent.name,
                    "second_name": former_partner.name,
                    "points": agent.relationship_points.get(former_partner.id, 0),
                    "stage": "friends",
                    "stage_changed": True,
                    "reason": "dating relationship ended when an agent died",
                })
                print("{} and {} are no longer dating because {} died.".format(
                    agent.name, former_partner.name, agent.name
                ))
            agent.dating_partner_id = None
            agent.dating_since_turn = None

        living_children = [
            child for child in self.agents
            if child.id != agent.id and child.id in agent.children_ids
        ]
        if living_children and agent.wealth > 0:
            inherited_amount, remainder = divmod(agent.wealth, len(living_children))
            for index, child in enumerate(sorted(living_children, key=lambda item: item.id)):
                amount = inherited_amount + (1 if index < remainder else 0)
                if amount > 0:
                    self._transfer_wealth(
                        agent, child, amount,
                        "inheritance from Agent {}".format(agent.id),
                        world_obj.turnNo + 1, world_obj,
                    )
        location = (agent.pos_x, agent.pos_y)
        if agent.hospital_visit_event is not None:
            agent.hospital_visit_event["outcome"] = "died during treatment"
            agent.hospital_visit_event["death_turn"] = world_obj.turnNo + 1
            agent.hospital_visit_event = None
        shared_occupants = world_obj.school_occupants.get(location)
        if shared_occupants is None:
            shared_occupants = world_obj.grocery_occupants.get(location)
        if shared_occupants is None:
            shared_occupants = world_obj.hospital_occupants.get(location)
        if shared_occupants is None:
            shared_occupants = world_obj.houses.get(location)
        if shared_occupants is not None:
            shared_occupants.discard(agent.id)
            if world_obj.agent_grid[agent.pos_x][agent.pos_y] == agent.id:
                world_obj.agent_grid[agent.pos_x][agent.pos_y] = (
                    next(iter(shared_occupants)) if shared_occupants else 0
                )
        else:
            world_obj.agent_grid[agent.pos_x][agent.pos_y] = 0
        world_obj.death_events.append({
            "turn": world_obj.turnNo + 1,
            "agent_id": agent.id,
            "age": agent.age,
            "cause": cause,
        })
        self.agents.remove(agent)
        print("Agent {} died from {} at age {}.".format(agent.id, cause, agent.age))

    def print_stat_card(self, world_obj):
        """Print the final building, employment and communication history."""
        print("\n" + "=" * 58)
        print("POST-GAME STAT CARD")
        print("=" * 58)
        print("Turns completed: {}".format(world_obj.turnNo))
        print("Buildings: {} ({} open jobs)".format(
            world_obj.building_count, world_obj.open_jobs
        ))

        deaths_by_agent = {
            event["agent_id"]: event for event in world_obj.death_events
        }
        print("\nAgent outcomes:")
        for agent in self.all_agents:
            death = deaths_by_agent.get(agent.id)
            if death:
                print("  Agent {}: DIED at age {} (cause: {}); end intelligence: {}; personality: {}; gender: {}; ethnicity: {}; religion: {}".format(
                    agent.id, death["age"], death["cause"], agent.intelligence,
                    agent.personality_type, agent.gender, agent.ethnicity, agent.religion
                ))
            else:
                print("  Agent {}: alive; end intelligence: {}; personality: {}; gender: {}; ethnicity: {}; religion: {}".format(
                    agent.id, agent.intelligence, agent.personality_type, agent.gender,
                    agent.ethnicity, agent.religion
                ))

        print("\nHiring history:")
        if world_obj.hiring_events:
            for event in world_obj.hiring_events:
                x, y = event["position"]
                print("  Turn {}: Agent {} got the {} at the {} ({}, {})".format(
                    event["turn"], event["agent_id"], event["job"],
                    building_names[event["building_type"]], x, y
                ))
        else:
            print("  No agents were hired.")

        rejections = [
            event for event in world_obj.job_application_events
            if not event["hired"]
        ]
        print("\nRejected job applications:")
        if rejections:
            for event in rejections:
                x, y = event["position"]
                print("  Turn {}: Agent {} was rejected from the {} at the {} "
                      "({}, {}) (score: {}; required: {}).".format(
                    event["turn"], event["agent_id"], event["job"],
                    building_names[event["building_type"]], x, y,
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("\nHouse history:")
        if world_obj.house_events:
            for event in world_obj.house_events:
                x, y = event["position"]
                if event["event"] == "evicted":
                    print("  Turn {}: Agent {} was evicted from the {} at ({}, {}); mental health is now {}/100".format(
                        event["turn"], event["agent_id"], building_names[event["house_type"]], x, y,
                        event["mental_health"]
                    ))
                else:
                    action = "bought" if event["event"] == "bought" else "paid rent for"
                    print("  Turn {}: Agent {} {} the {} at ({}, {}) for ${:,}; wealth is now ${:,}".format(
                        event["turn"], event["agent_id"], action,
                        building_names[event["house_type"]], x, y, event["amount"], event["wealth"]
                    ))
        else:
            print("  None")

        print("\nRelationship history:")
        if world_obj.relationship_events:
            for event in world_obj.relationship_events:
                if event.get("reason"):
                    print("  Turn {}: {} and {}; {} ({} points).".format(
                        event["turn"], event["first_name"], event["second_name"],
                        event["reason"], event["points"]
                    ))
                else:
                    print("  Turn {}: {} and {}: {} points, {}.".format(
                        event["turn"], event["first_name"], event["second_name"],
                        event["points"], event["stage"]
                    ))
        else:
            print("  None")

        print("\nBirths:")
        if world_obj.birth_events:
            for event in world_obj.birth_events:
                ethnicity = ", ".join(
                    "{}% {}".format(round(percentage, 1), name)
                    for name, percentage in sorted(event["ethnicity_percentages"].items())
                )
                x, y = event["position"]
                print("  Turn {}: Agent {} was born to {} and {}; spawned at ({}, {}); "
                      "age: {}; natural death age: {}; intelligence: {}; willpower: {}; "
                      "personality: {}; gender: {}; ethnicity: {}; religion: {}.".format(
                    event["turn"], event["agent_id"],
                    event["parent_names"][0], event["parent_names"][1], x, y,
                    event["age"], event["death_age"], event["intelligence"],
                    event["willpower"], event["personality"], event["gender"],
                    ethnicity, event["religion"]
                ))
        else:
            print("  None")

        print("\nDisease history:")
        if world_obj.disease_events:
            for event in world_obj.disease_events:
                if event.get("source") == "natural":
                    print("  Turn {}: Agent {} contracted {} naturally".format(
                        event["turn"], event["agent_id"], event["disease"]
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], event["disease"],
                        event["source_id"]
                    ))
        else:
            print("  None")

        print("\nSchool history:")
        if world_obj.school_events:
            for event in world_obj.school_events:
                if event["event"] == "enrolled":
                    x, y = event["position"]
                    print("  Turn {}: Agent {} enrolled at ({}, {})".format(
                        event["turn"], event["agent_id"], x, y
                    ))
                else:
                    print("  Turn {}: Agent {} graduated; intelligence is now {}".format(
                        event["turn"], event["agent_id"], event["intelligence"]
                    ))
        else:
            print("  None")

        print("\nHospital visits:")
        if world_obj.hospital_events:
            for event in world_obj.hospital_events:
                x, y = event["position"]
                diseases = ", ".join(event["diseases"])
                if event["outcome"] == "cured":
                    print("  Agent {} admitted on turn {} with {}; cured after {} turn(s) on turn {} at ({}, {}).".format(
                        event["agent_id"], event["admitted_turn"], diseases,
                        event["turns_in_hospital"], event["cured_turn"], x, y
                    ))
                elif event["outcome"] == "died during treatment":
                    print("  Agent {} admitted on turn {} with {}; died during treatment on turn {} at ({}, {}).".format(
                        event["agent_id"], event["admitted_turn"], diseases,
                        event["death_turn"], x, y
                    ))
                else:
                    print("  Agent {} admitted on turn {} with {}; still in treatment at ({}, {}).".format(
                        event["agent_id"], event["admitted_turn"], diseases, x, y
                    ))
        else:
            print("  None")

        print("\nGrocery purchases:")
        if world_obj.grocery_events:
            for event in world_obj.grocery_events:
                print("  Turn {}: Agent {} bought food for ${:,}; wealth is now ${:,}.".format(
                    event["turn"], event["agent_id"], event["cost"], event["wealth"]
                ))
        else:
            print("  None")

        print("\nJob upgrades and vacancies:")
        if world_obj.job_quit_events:
            for event in world_obj.job_quit_events:
                x, y = event["position"]
                print("  Turn {}: Agent {} {}; {} at ({}, {}) reopened".format(
                    event["turn"], event["agent_id"], event["reason"],
                    event["job"], x, y
                ))
        else:
            print("  None")

        print("\nDeaths:")
        if world_obj.death_events:
            for event in world_obj.death_events:
                print("  Turn {}: Agent {} died from {} at age {}".format(
                    event["turn"], event["agent_id"], event["cause"], event["age"]
                ))
        else:
            print("  None")

        print("\nAgent health:")
        for agent in self.all_agents:
            diseases = ", ".join(sorted(agent.diseases)) or "none"
            print("  Agent {}: {}/100; diseases: {}".format(agent.id, agent.health, diseases))

        print("\nAgent mental health:")
        for agent in self.all_agents:
            print("  Agent {}: {}/100".format(agent.id, agent.mental_health))

        print("\nAgent hunger:")
        for agent in self.all_agents:
            print("  Agent {}: {}/{}".format(
                agent.id, agent.hunger, agent.hunger_max
            ))

        print("\nAgent wealth:")
        for agent in self.all_agents:
            print("  Agent {}: ${}".format(agent.id, agent.wealth))

        self.print_wealth_gini_graph()

        print("\nAgent jobs:")
        for agent in self.all_agents:
            print("  Agent {}: {}".format(agent.id, agent.job or "unemployed"))

        print("\nCommunications:")
        if world_obj.communication_events:
            for event in world_obj.communication_events:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: {} interacted with {}; shared building-free locations: {}".format(
                    event["turn"], event["sender_name"], event["receiver_name"], locations
                ))
        else:
            print("  No messages were exchanged.")

        print("\nMoney transfers:")
        if world_obj.money_transfer_events:
            for event in world_obj.money_transfer_events:
                print("  Turn {}: {} transferred ${:,} to {} ({}).".format(
                    event["turn"], event["from_name"], event["amount"],
                    event["to_name"], event["reason"]
                ))
        else:
            print("  None")

        print("\nAgents previously interacted with:")
        for agent in self.all_agents:
            names = ", ".join(agent.interacted_agents) or "none"
            print("  {}: {}".format(agent.name, names))
        print("=" * 58)

    def print_wealth_gini_graph(self):
        """Print an ASCII Lorenz curve and Gini coefficient for final wealth."""
        for line in self.wealth_gini_graph_lines():
            print(line)

    def wealth_gini_graph_lines(self):
        """Return the final wealth Lorenz graph as lines for console or GUI output."""
        wealth_values = sorted(max(0, agent.wealth) for agent in self.all_agents)
        lines = ["", "Wealth inequality (Lorenz curve; all simulation agents):"]
        if not wealth_values:
            lines.append("  No agent wealth data available.")
            return lines

        count = len(wealth_values)
        total_wealth = sum(wealth_values)
        gini = self.wealth_gini_coefficient()

        width, height = 30, 10
        cumulative = [0]
        for wealth in wealth_values:
            cumulative.append(cumulative[-1] + wealth)

        graph = []
        for row in range(height + 1):
            graph.append([" "] * (width + 1))

        for column in range(width + 1):
            population_share = column / width
            agent_position = population_share * count
            lower_index = min(int(agent_position), count)
            fraction = agent_position - lower_index
            partial_wealth = cumulative[lower_index]
            if lower_index < count:
                partial_wealth += fraction * wealth_values[lower_index]
            wealth_share = partial_wealth / total_wealth if total_wealth else population_share
            lorenz_row = round((1 - wealth_share) * height)
            equality_row = round((1 - population_share) * height)
            graph[equality_row][column] = "."
            graph[lorenz_row][column] = "+" if lorenz_row == equality_row else "*"

        for row, cells in enumerate(graph):
            percentage = 100 - row * 10
            lines.append("  {:>3}% |{}".format(percentage, "".join(cells)))
        lines.append("      +{}".format("-" * (width + 1)))
        lines.append("       0%{}100% (cumulative population)".format(" " * (width - 5)))
        lines.append("  . Equality line   * Wealth distribution   + Overlap")
        lines.append("  Gini coefficient: {:.3f} (0 = equal wealth, 1 = maximum inequality)".format(gini))
        return lines

    def wealth_gini_coefficient(self):
        """Calculate the wealth Gini coefficient for all simulation agents."""
        wealth_values = sorted(max(0, agent.wealth) for agent in self.all_agents)
        if not wealth_values:
            return None
        total_wealth = sum(wealth_values)
        if total_wealth == 0:
            return 0.0
        count = len(wealth_values)
        weighted_sum = sum(
            (2 * index - count - 1) * wealth
            for index, wealth in enumerate(wealth_values, start=1)
        )
        return weighted_sum / (count * total_wealth)

    def print_batch_report(self, world_obj, start_turn, end_turn):
        """Print building and job events produced during one batch."""
        entries = [event for event in world_obj.building_entries
                   if start_turn <= event["turn"] <= end_turn]
        hires = [event for event in world_obj.hiring_events
                 if start_turn <= event["turn"] <= end_turn]
        rejections = [
            event for event in world_obj.job_application_events
            if not event["hired"]
            and start_turn <= event["turn"] <= end_turn
        ]
        quits = [event for event in world_obj.job_quit_events
                 if start_turn <= event["turn"] <= end_turn]
        school_events = [event for event in world_obj.school_events
                         if start_turn <= event["turn"] <= end_turn]
        grocery_events = [event for event in world_obj.grocery_events
                          if start_turn <= event["turn"] <= end_turn]
        disease_events = [event for event in world_obj.disease_events
                          if start_turn <= event["turn"] <= end_turn]
        communications = [
            event for event in world_obj.communication_events
            if start_turn <= event["turn"] <= end_turn
        ]
        money_transfers = [
            event for event in world_obj.money_transfer_events
            if start_turn <= event["turn"] <= end_turn
        ]
        house_events = [event for event in world_obj.house_events
                        if start_turn <= event["turn"] <= end_turn]
        relationship_events = [event for event in world_obj.relationship_events
                               if start_turn <= event["turn"] <= end_turn]
        births = [event for event in world_obj.birth_events
                  if start_turn <= event["turn"] <= end_turn]
        print("\n" + "-" * 58)
        print("BATCH REPORT: Turns {}-{}".format(start_turn, end_turn))
        print("Building entries:")
        if entries:
            for event in entries:
                x, y = event["position"]
                print("  Turn {}: Agent {} entered the {} at ({}, {})".format(
                    event["turn"], event["agent_id"], building_names[event["building_type"]], x, y
                ))
        else:
            print("  None")

        print("Births:")
        if births:
            for event in births:
                ethnicity = ", ".join(
                    "{}% {}".format(round(percentage, 1), name)
                    for name, percentage in sorted(event["ethnicity_percentages"].items())
                )
                x, y = event["position"]
                print("  Turn {}: Agent {} born to {} and {}; spawned at ({}, {}); "
                      "age: {}; natural death age: {}; intelligence: {}; willpower: {}; "
                      "personality: {}; gender: {}; ethnicity: {}; religion: {}.".format(
                    event["turn"], event["agent_id"],
                    event["parent_names"][0], event["parent_names"][1], x, y,
                    event["age"], event["death_age"], event["intelligence"],
                    event["willpower"], event["personality"], event["gender"],
                    ethnicity, event["religion"]
                ))
        else:
            print("  None")

        print("Relationship changes:")
        if relationship_events:
            for event in relationship_events:
                if event.get("reason"):
                    print("  Turn {}: {} and {}; {}.".format(
                        event["turn"], event["first_name"], event["second_name"],
                        event["reason"]
                    ))
                else:
                    print("  Turn {}: {} and {} have {} relationship points ({}){}".format(
                        event["turn"], event["first_name"], event["second_name"],
                        event["points"], event["stage"],
                        " (stage changed)" if event["stage_changed"] else ""
                    ))
        else:
            print("  None")

        print("House events:")
        if house_events:
            for event in house_events:
                x, y = event["position"]
                if event["event"] == "evicted":
                    print("  Turn {}: Agent {} evicted from the {} at ({}, {}); mental health {}/100".format(
                        event["turn"], event["agent_id"], building_names[event["house_type"]], x, y,
                        event["mental_health"]
                    ))
                else:
                    action = "bought" if event["event"] == "bought" else "paid rent for"
                    print("  Turn {}: Agent {} {} the {} for ${:,}; wealth ${:,}".format(
                        event["turn"], event["agent_id"], action,
                        building_names[event["house_type"]], event["amount"], event["wealth"]
                    ))
        else:
            print("  None")

        print("Rejected job applications:")
        if rejections:
            for event in rejections:
                x, y = event["position"]
                print("  Turn {}: Agent {} was rejected from the {} at the {} "
                      "({}, {}) (score: {}; required: {}).".format(
                    event["turn"], event["agent_id"], event["job"],
                    building_names[event["building_type"]], x, y,
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("Disease events:")
        if disease_events:
            for event in disease_events:
                if event.get("source") == "natural":
                    print("  Turn {}: Agent {} contracted {} naturally".format(
                        event["turn"], event["agent_id"], event["disease"]
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], event["disease"],
                        event["source_id"]
                    ))
        else:
            print("  None")

        print("School:")
        if school_events:
            for event in school_events:
                if event["event"] == "enrolled":
                    x, y = event["position"]
                    print("  Turn {}: Agent {} enrolled at ({}, {})".format(
                        event["turn"], event["agent_id"], x, y
                    ))
                else:
                    print("  Turn {}: Agent {} graduated; intelligence is now {}".format(
                        event["turn"], event["agent_id"], event["intelligence"]
                    ))
        else:
            print("  None")

        print("Jobs reopened:")
        if quits:
            for event in quits:
                x, y = event["position"]
                print("  Turn {}: Agent {} {}; {} at ({}, {}) reopened".format(
                    event["turn"], event["agent_id"], event["reason"],
                    event["job"], x, y
                ))
        else:
            print("  None")

        print("Grocery purchases:")
        if grocery_events:
            for event in grocery_events:
                print("  Turn {}: Agent {} bought food for ${:,}; health {}, mental health {}, wealth ${:,}.".format(
                    event["turn"], event["agent_id"], event["cost"],
                    event["health"], event["mental_health"], event["wealth"]
                ))
        else:
            print("  None")

        deaths = [event for event in world_obj.death_events
                  if start_turn <= event["turn"] <= end_turn]
        print("Deaths:")
        if deaths:
            for event in deaths:
                print("  Turn {}: Agent {} died from {} at age {}".format(
                    event["turn"], event["agent_id"], event["cause"], event["age"]
                ))
        else:
            print("  None")

        print("Agents hired:")
        if hires:
            for event in hires:
                print("  Turn {}: Agent {} got the {} (score: {}; required: {})".format(
                    event["turn"], event["agent_id"], event["job"],
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("Communications:")
        if communications:
            for event in communications:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: {} interacted with {}; shared building-free locations: {}".format(
                    event["turn"], event["sender_name"], event["receiver_name"], locations
                ))
        else:
            print("  None")

        print("Money transfers:")
        if money_transfers:
            for event in money_transfers:
                print("  Turn {}: {} transferred ${:,} to {} ({}).".format(
                    event["turn"], event["from_name"], event["amount"],
                    event["to_name"], event["reason"]
                ))
        else:
            print("  None")
        print("Agent wealth:")
        for agent in self.all_agents:
            print("  Agent {}: ${:,}".format(agent.id, agent.wealth))
        print("Open jobs: {}".format(world_obj.open_jobs))
        print("-" * 58)
