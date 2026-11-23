import random

try:
    from .agent import Agent
    from .migration import process_migration
    from .config import agent_count, building_names, grocery_food_cost, grocery_hunger_threshold
    from .disease import (
        activate_pending_infections, combine_parent_immune_systems,
        disease_name, process_disease_turn, DISEASE_ORDER, is_immune,
    )
except ImportError:
    try:
        from pythonFiles.agent import Agent
        from pythonFiles.migration import process_migration
        from pythonFiles.config import agent_count, building_names, grocery_food_cost, grocery_hunger_threshold
        from pythonFiles.disease import (
            activate_pending_infections, combine_parent_immune_systems,
            disease_name, process_disease_turn, DISEASE_ORDER, is_immune,
        )
    except ImportError:
        from agent import Agent
        from migration import process_migration
        from config import agent_count, building_names, grocery_food_cost, grocery_hunger_threshold
        from disease import (
            activate_pending_infections, combine_parent_immune_systems,
            disease_name, process_disease_turn, DISEASE_ORDER, is_immune,
        )


class Population:
    def __init__(self, world_obj, count=None):
        # Read updated agent count dynamically from world_obj.config if count isn't explicitly passed
        if count is None:
            config = getattr(world_obj, "config", {})
            # Look in nested "Agent & Population" category first, then top-level flat key
            agent_cfg = config.get("Agent & Population", config) if isinstance(config, dict) else {}
            count = agent_cfg.get("agent_count", config.get("agent_count", agent_count))

        predefined = bool(getattr(world_obj, "config", {}).get(
            "start_with_predefined_positions", False
        ))
        self.agents = [
            Agent(agent_id=i, world_obj=world_obj,
                  age=random.randint(1, 80) if predefined else None)
            for i in range(count)
        ]
        self.all_agents = list(self.agents)
        world_obj.agent_lookup = {agent.id: agent for agent in self.all_agents}
        self.next_agent_id = count
        self.pregnancies = {}
        if predefined:
            self._initialize_predefined_start(world_obj)

    def _initialize_predefined_start(self, world_obj):
        """Seed a varied starting population while preserving normal agent traits."""
        # Pair some agents, with married and dating relationships represented
        # using the same fields as relationships formed during play.
        shuffled = list(self.agents)
        random.shuffle(shuffled)
        household_groups = []
        index = 0
        while index + 1 < len(shuffled):
            if random.random() < 0.45:
                first, second = shuffled[index:index + 2]
                index += 2
                first.dating_partner_id = second.id
                second.dating_partner_id = first.id
                first.dating_since_turn = second.dating_since_turn = world_obj.turnNo
                if random.random() < 0.5:
                    first.marital_status = second.marital_status = "married"
                household_groups.append([first, second])
            else:
                household_groups.append([shuffled[index]])
                index += 1
        if index < len(shuffled):
            household_groups.append([shuffled[index]])

        # Give some minors a parent from an older household, so shared homes
        # follow the same owner/partner/child rule as homes acquired later.
        for child in [agent for agent in shuffled if agent.age < 18]:
            if random.random() >= 0.65:
                continue
            existing_group = next(
                (group for group in household_groups if child in group), None
            )
            if existing_group is not None and len(existing_group) > 1:
                continue
            possible_groups = [
                group for group in household_groups
                if len(group) < 6
                and group[0].age >= 25
                and group[0].region == child.region
                and child not in group
            ]
            if not possible_groups:
                continue
            group = random.choice(possible_groups)
            parent = group[0]
            child.parent_ids.add(parent.id)
            parent.children_ids.add(child.id)
            group.append(child)
            if existing_group is not None:
                household_groups.remove(existing_group)

        # Jobs are assigned from real openings, with jobless agents and the two
        # less common job types weighted lower than the other available jobs.
        for agent in self.agents:
            if agent.age < 15:
                continue
            openings = [
                (location, world_obj.grid[location[0]][location[1]])
                for location, holders in world_obj.building_jobs.items()
                for _ in range(max(0, world_obj.job_capacities[location] - len(holders)))
            ]
            if not openings or random.random() < 0.25:
                continue
            selected = random.choices(
                openings,
                weights=[0.2 if opening[1] in (2, 5) else 1.0
                         for opening in openings],
                k=1,
            )[0]
            location, building_type = selected
            world_obj.building_jobs[location].add(agent.id)
            agent.job = world_obj.job_name(building_type)
            agent.employed_at = location

        for agent in self.agents:
            building_type = world_obj.job_type(agent.job) if agent.job else None
            annual_wage = (
                world_obj.job_income_per_year(building_type)
                * world_obj.regions[agent.region]["wage_multiplier"]
                if building_type is not None else 0
            )
            midpoint = annual_wage * agent.age
            agent.wealth = int(round(midpoint * random.uniform(0.5, 1.5)))

            if random.random() < 0.10:
                susceptible = [
                    disease for disease in DISEASE_ORDER
                    if not is_immune(agent.immune_system, disease)
                ]
                if susceptible:
                    agent.diseases.add(random.choice(susceptible))

        # Each household gets a randomly selected available home. Premium
        # houses (type 7) are deliberately less likely than other home types.
        for group in household_groups:
            if len(group) > 6 or len({agent.region for agent in group}) != 1:
                continue
            region_id = group[0].region
            choices = [
                location for location in world_obj.houses
                if world_obj.region_of(*location) == region_id
                and not any(agent.house == location for agent in self.agents)
            ]
            if not choices:
                continue
            location = random.choices(
                choices,
                weights=[0.2 if world_obj.grid[row][col] == 7 else 1.0
                         for row, col in choices],
                k=1,
            )[0]
            owner = next((agent for agent in group if agent.age >= 18), group[0])
            world_obj.house_owners[location] = owner.id
            for agent in group:
                agent.house = location
                world_obj.houses[location].add(agent.id)

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
        world_obj.agent_lookup[newborn.id] = newborn
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
            region_id=random.choice((first_parent.region, second_parent.region)),
            original_immune_system=combine_parent_immune_systems(
                first_parent.original_immune_system,
                second_parent.original_immune_system,
            ),
        )
        self.next_agent_id += 1
        self.agents.append(newborn)
        self.all_agents.append(newborn)
        world_obj.agent_lookup[newborn.id] = newborn
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

    @staticmethod
    def _are_siblings(first, second):
        return bool(first.parent_ids & second.parent_ids)

    @staticmethod
    def _advance_relationship(first, second, turn, world_obj):
        """Award interaction points and establish friendship or exclusive dating."""
        previous_points = first.relationship_points.get(second.id, 0)
        old_stage = Population._relationship_stage(first, second, previous_points)
        is_parent_child = (
            second.id in first.parent_ids or first.id in second.parent_ids
        )
        are_siblings = Population._are_siblings(first, second)
        points = min(10, previous_points + 5) if is_parent_child else previous_points + 5
        first.relationship_points[second.id] = points
        second.relationship_points[first.id] = points

        can_date_each_other = (
            not is_parent_child
            and not are_siblings
            and first.marital_status != "married"
            and second.marital_status != "married"
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
        if random.random() >= giver.empathy:
            return None
        return giver, receiver, amount, reason

    def _update_vaccine_research(self, world_obj):
        """Advance vaccine research progress based on hospital workers' intelligence."""
        hospital_workers = [
            a for a in self.agents 
            if a.job == "Hospital job" 
            and a.hospitalized_at is None 
            and not a.diseases
        ]
        if not hospital_workers:
            return
            
        total_intel = sum(a.intelligence for a in hospital_workers)
        # Scaling factor to determine research speed
        scaling_factor = 0.0001 
        
        from disease import DISEASES
        for d_id in world_obj.vaccine_progress:
            if d_id not in world_obj.available_vaccines:
                world_obj.vaccine_progress[d_id] += total_intel * scaling_factor
                if world_obj.vaccine_progress[d_id] >= 1.0:
                    world_obj.available_vaccines.add(d_id)
                    print("VACCINE ALERT: A vaccine for {} has been researched and is now available!".format(
                        DISEASES[d_id].name
                    ))

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

    def step_agents(self, world_obj):
        self._update_vaccine_research(world_obj)
        activate_pending_infections(self.agents)

        # Age advances by the selected calendar interval; survival remains tied
        # to each agent's natural death age, which is measured in years.
        age_increment = getattr(world_obj, "time_step_days", 365.25) / 365.25
        for agent in list(self.agents):
            previous_age = agent.age
            if agent.age < agent.death_age:
                agent.age = min(agent.death_age, agent.age + age_increment)
            if (agent.parent_ids and agent.birth_turn is not None
                    and previous_age < 10 <= agent.age):
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
        for agent in self.agents:
            agent.move(world_obj)

        current_sightings = {agent.id: set() for agent in self.agents}
        for index, first in enumerate(self.agents):
            for second in self.agents[index + 1:]:
                if max(abs(first.pos_x - second.pos_x), abs(first.pos_y - second.pos_y)) <= 1:
                    current_sightings[first.id].add(second.id)
                    current_sightings[second.id].add(first.id)
                    newly_visible = (
                        second.id not in first.visible_agent_ids
                        and first.id not in second.visible_agent_ids
                    )
                    if newly_visible:
                        self.share_information(first, second, world_obj)

        for agent in self.agents:
            agent.visible_agent_ids = current_sightings[agent.id]
        self._process_marriages(world_obj)
        self._process_births(world_obj)
        process_migration(self, world_obj)
        process_disease_turn(self.agents, world_obj)
        for agent in list(self.agents):
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
                continue
            agent.earn_income(world_obj)
            agent.update_health(world_obj)
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
            else:
                agent.advance_hospital_stay(world_obj)
                agent.advance_school(world_obj)
                agent.advance_house_stay(world_obj)
        world_obj.turnNo +=1
        world_obj.elapsed_days += getattr(world_obj, "time_step_days", 365.25)

    def _support_young_children(self, world_obj):
        """Transfer grocery money when young children are hungry and parents can cover it."""
        turn = world_obj.turnNo + 1
        for child in self.agents:
            threshold = child._get_cfg_val(world_obj, "Grocery & Needs",
                                           "grocery_hunger_threshold", grocery_hunger_threshold)
            if (not child.parent_ids or child.birth_turn is None
                    or child.age >= 15 or child.hunger >= threshold):
                continue
            shortfall = max(0, world_obj.food_cost(child.region) - child.wealth)
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
        """Conceive after the existing relationship wait and deliver after nine months."""
        turn = world_obj.turnNo + 1
        agents_by_id = {agent.id: agent for agent in self.agents}
        gestation_days = 9 * (365.25 / 12)
        elapsed_days = getattr(world_obj, "elapsed_days", 0.0)
        days_at_turn_end = elapsed_days + getattr(world_obj, "time_step_days", 365.25)
        for mother_id, pregnancy in list(self.pregnancies.items()):
            mother = agents_by_id.get(mother_id)
            father = agents_by_id.get(pregnancy["father_id"])
            if mother is None or father is None:
                del self.pregnancies[mother_id]
                continue
            if days_at_turn_end - pregnancy["start_day"] >= gestation_days:
                self.birth_child(world_obj, mother, father)
                del self.pregnancies[mother_id]

        for first in list(self.agents):
            partner_id = first.dating_partner_id
            if (partner_id is None
                    or first.dating_since_turn is None
                    or turn - first.dating_since_turn <= 5):
                continue
            second = agents_by_id.get(partner_id)
            if (second is None or second.dating_partner_id != first.id
                    or self._are_siblings(first, second)
                    or first.children_ids.intersection(second.children_ids)):
                continue
            mother, father = (first, second) if first.gender == "female" else (second, first)
            if (mother.gender != "female" or mother.age < 18
                    or mother.id in self.pregnancies):
                continue
            self.pregnancies[mother.id] = {
                "father_id": father.id,
                "start_day": elapsed_days,
            }

    def _process_marriages(self, world_obj):
        """Marry dating couples after five turns if they can cover the wedding."""
        turn = world_obj.turnNo + 1
        agents_by_id = {agent.id: agent for agent in self.agents}
        for first in self.agents:
            partner_id = first.dating_partner_id
            if (partner_id is None or first.id > partner_id
                    or first.dating_since_turn is None
                    or turn - first.dating_since_turn < 5):
                continue
            second = agents_by_id.get(partner_id)
            if (second is None or second.dating_partner_id != first.id
                    or self._are_siblings(first, second)
                    or first.marital_status == "married"
                    or second.marital_status == "married"
                    or first.wealth + second.wealth < 2000):
                continue

            remaining_cost = 2000
            for agent in sorted((first, second), key=lambda item: item.id):
                amount = min(agent.wealth, remaining_cost)
                agent.wealth -= amount
                remaining_cost -= amount

            first.marital_status = second.marital_status = "married"
            world_obj.relationship_events.append({
                "turn": turn,
                "first_id": first.id,
                "second_id": second.id,
                "first_name": first.name,
                "second_name": second.name,
                "points": first.relationship_points.get(second.id, 0),
                "stage": "married",
                "stage_changed": True,
                "reason": "held a wedding costing $2,000",
            })
            print("{} and {} got married after dating for five turns; their wedding cost $2,000.".format(
                first.name, second.name
            ))

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
                print("  Agent {}: DIED at age {} (cause: {}); birthplace: {}; end intelligence: {}; personality: {}; gender: {}; ethnicity: {}; religion: {}".format(
                    agent.id, death["age"], death["cause"], agent.birth_place,
                    agent.intelligence,
                    agent.personality_type, agent.gender, agent.ethnicity, agent.religion
                ))
            else:
                print("  Agent {}: alive; birthplace: {}; end intelligence: {}; personality: {}; gender: {}; ethnicity: {}; religion: {}".format(
                    agent.id, agent.birth_place, agent.intelligence,
                    agent.personality_type, agent.gender,
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
                        event["turn"], event["agent_id"], disease_name(event["disease"])
                    ))
                elif event.get("source") == "user":
                    print("  Turn {}: Agent {} was exposed to {} by the user".format(
                        event["turn"], event["agent_id"], disease_name(event["disease"])
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], disease_name(event["disease"]),
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
                diseases = ", ".join(
                    disease_name(disease) for disease in event["diseases"]
                )
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
            diseases = ", ".join(
                disease_name(disease) for disease in sorted(agent.diseases)
            ) or "none"
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
                print("  Turn {}: {} shared map information with {}.".format(
                    event["turn"], event["sender_name"], event["receiver_name"]
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
                        event["turn"], event["agent_id"], disease_name(event["disease"])
                    ))
                elif event.get("source") == "user":
                    print("  Turn {}: Agent {} was exposed to {} by the user".format(
                        event["turn"], event["agent_id"], disease_name(event["disease"])
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], disease_name(event["disease"]),
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
                print("  Turn {}: {} shared map information with {}.".format(
                    event["turn"], event["sender_name"], event["receiver_name"]
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
