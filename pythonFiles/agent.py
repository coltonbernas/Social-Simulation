import random

try:
    from .config import (
        grid_rows, grid_cols, health_min, health_max, starting_health_min,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn, hunger_drain_per_step, starting_wealth,
        type_1_income_per_turn, type_2_income_per_turn,
        low_wealth_threshold, low_wealth_stress_turns,
        grocery_hunger_threshold, grocery_food_cost,
        grocery_food_health_restore, grocery_food_mental_restore,
        mental_health_recovery_per_turn,
        stress_mental_health_initial_drain, stress_mental_health_sustained_drain,
        hospital_stay_duration_turns, building_names,
    )
except ImportError:
    from config import (
        grid_rows, grid_cols, health_min, health_max, starting_health_min,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn, hunger_drain_per_step, starting_wealth,
        type_1_income_per_turn, type_2_income_per_turn,
        low_wealth_threshold, low_wealth_stress_turns,
        grocery_hunger_threshold, grocery_food_cost,
        grocery_food_health_restore, grocery_food_mental_restore,
        mental_health_recovery_per_turn,
        stress_mental_health_initial_drain, stress_mental_health_sustained_drain,
        hospital_stay_duration_turns, building_names,
    )


def random_intelligence():
    """Sample an IQ-style score using the percentages in the supplied chart."""
    score_range = random.choices(
        population=[(40, 69), (70, 79), (80, 89), (90, 109), (110, 119), (120, 129), (130, 145)],
        weights=[2.2, 6.7, 16.1, 50.0, 16.1, 6.7, 2.2],
        k=1,
    )[0]
    return random.randint(*score_range)


class Agent:
    def __init__(self, agent_id, world_obj, rows=grid_rows, cols=grid_cols, age=None):
        self.id = agent_id+1
        self.name = "Agent {}".format(self.id)
        self.age = random.randint(1, 30) if age is None else age
        self.death_age = random.randint(80, 100)
        self.intelligence = random_intelligence()
        # Initial health uses its own range; health_min remains the simulation
        # floor for later damage and recovery.
        spawn_health_min = max(health_min, min(starting_health_min, health_max))
        self.health = random.randint(spawn_health_min, health_max)
        self.last_health_damage_cause = None
        self.diseases = set()
        #Gonna make this affect hard decisions and getting a job
        self.willpower = random.randint(0, 100)
        self.mental_health = 100
        self.wealth = starting_wealth
        self.house = None
        self.house_turns_since_payment = 0
        self.low_wealth_turns = 0
        self.job = None
        self.employed_at = None
        self.returning_to_job = False
        self.hospitalized_at = None
        self.hospital_stay_turns = 0
        self.hospital_visit_event = None
        # Building coordinates map to the opening version last attempted.
        self.applied_buildings = {}
        self.hunger_max = 100
        self.hunger = self.hunger_max
        self.active_stressful_events = set()
        self.political_status = None
        self.birth_place = None
        self.birth_date = None
        self.ethnicity = None
        self.immigration_status = None
        self.personality_type = random.choice((
            "introverted", "extroverted", "ambivert"
        ))
        self.inheritance = None
        self.genes = []
        self.religion = None
        self.education = None
        self.school_completed = False
        self.schooling_at = None
        self.school_turns = 0
        self.marital_status = None
        self.morality = None
        self.empathy = None
        self.resilience = None
        self.agreeableness = None
        self.openness = None
        self.implusiveness = None
        self.creativity = None
        self.needs = {}
        self.confidence = None

        self.pos_x, self.pos_y  = self.get_safe_spawn_pos(world_obj, rows, cols)
        # Cells observed or reported to contain no building.
        self.known_empty = set()
        self.visited_positions = {(self.pos_x, self.pos_y)}
        self.position_visits = {(self.pos_x, self.pos_y): 1}
        self.previous_position = None
        self.interacted_agents = []
        self.interaction_last_turn = {}
        self.visible_agent_ids = set()

        world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        print("Agent {} spawned at ({},{}); age: {}; natural death age: {}; "
              "intelligence: {}; willpower: {}; personality: {}".format(
            self.id, self.pos_x, self.pos_y, self.age, self.death_age,
            self.intelligence, self.willpower, self.personality_type
        ))

    def get_safe_spawn_pos(self, world_obj, rows, cols):
        attempts = 0
        max_attempts = 1000

        while attempts < max_attempts:
            x = random.randint(0, rows-1)
            y = random.randint(0, cols-1)

            if self.is_position_safe(x, y, world_obj, rows, cols):
                return x, y
            attempts += 1

        raise RuntimeError(
            "Could not find a valid spawn position"
        )

    def is_position_safe(self, x, y, world_obj, rows, cols):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] != 0:
                            return False
                    if world_obj.agent_grid[nx][ny] != 0:
                        return False
        return True

    def scan_surroundings(self, world_obj, rows, cols):
        visible_buildings = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = self.pos_x + dx, self.pos_y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] != 0:
                        visible_buildings.append((nx, ny))
        return visible_buildings

    def scan_empty_surroundings(self, world_obj, rows, cols):
        """Return nearby cells that do not contain buildings."""
        empty_locations = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = self.pos_x + dx, self.pos_y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] == 0:
                        empty_locations.append((nx, ny))
        return empty_locations

    def receive_message(self, empty_locations):
        """Remember cells another agent reports as building-free."""
        self.known_empty.update(empty_locations)

    def disease_transmission_probability(self, disease=None):
        """Chance of catching a disease from one infectious close contact."""
        contagiousness = (disease or {}).get("contagiousness", base_disease_transmission)
        # Lower health increases susceptibility; healthy agents retain a
        # modest baseline risk. Clamp to a valid probability.
        health_range = health_max - health_min
        health_fraction = (self.health - health_min) / health_range if health_range else 1.0
        susceptibility = 1.5 - health_fraction * 0.5
        return max(0.0, min(1.0, contagiousness * susceptibility))

    def catch_disease(self, disease="common_cold", contagiousness=None):
        """Try to acquire a disease; return True if this contact infects the agent."""
        if disease in self.diseases:
            return False
        if contagiousness is None:
            contagiousness = base_disease_transmission
        if random.random() >= self.disease_transmission_probability({"contagiousness": contagiousness}):
            return False
        self.diseases.add(disease)
        self.damage_health(disease_health_impact, "disease: {}".format(disease))
        return True

    def damage_health(self, amount, cause):
        """Reduce health and remember what caused the latest reduction."""
        previous_health = self.health
        self.health = max(health_min, self.health - amount)
        if self.health < previous_health:
            self.last_health_damage_cause = cause

    def update_health(self, world_obj=None):
        """Apply health changes, including starvation and stressful events."""
        self.hunger = max(0, self.hunger - hunger_drain_per_step)
        if not self.diseases and random.random() < disease_chance_per_turn:
            disease = "common_cold"
            self.diseases.add(disease)
            self.damage_health(disease_health_impact, "disease: {}".format(disease))
            if world_obj is not None:
                world_obj.disease_events.append({
                    "turn": world_obj.turnNo + 1,
                    "agent_id": self.id,
                    "disease": disease,
                    "source": "natural",
                    "health": self.health,
                })
            print("Agent {} naturally contracted {} (health: {}).".format(
                self.id, disease, self.health
            ))
        if self.diseases:
            disease = sorted(self.diseases)[0]
            self.damage_health(10, "disease: {}".format(disease))
        else:
            previous_health = self.health
            self.health = min(health_max, self.health + 1)
            if self.health > previous_health:
                self.last_health_damage_cause = None

        if self.hunger <= 0:
            self.damage_health(10, "hunger")

        self.update_stressful_events()

    def earn_income(self):
        """Add this turn's wages for the agent's current job."""
        if self.job == "Type 1 job":
            self.wealth += type_1_income_per_turn
        elif self.job == "Type 2 job":
            self.wealth += type_2_income_per_turn

    def advance_school(self, world_obj):
        """Count attendance turns and award intelligence after five turns."""
        if self.schooling_at is None or (self.pos_x, self.pos_y) != self.schooling_at:
            return
        self.school_turns += 1
        if self.school_turns >= 5:
            self.intelligence += 20
            self.school_completed = True
            self.schooling_at = None
            self.applied_buildings.clear()
            world_obj.school_events.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "event": "graduated",
                "intelligence": self.intelligence,
            })
            print("Agent {} completed school; intelligence increased by 20 to {}.".format(
                self.id, self.intelligence
            ))

    def can_seek_school(self, world_obj):
        if self.job is not None or self.school_completed or self.schooling_at is not None:
            return False
        available_jobs = [
            location for location, holder in world_obj.building_jobs.items()
            if holder is None
            and self.can_apply_for_type(world_obj.grid[location[0]][location[1]])
            and self.applied_buildings.get(location)
            != world_obj.job_opening_versions[location]
        ]
        school_nearby = any(
            max(abs(location[0] - self.pos_x), abs(location[1] - self.pos_y)) <= 1
            for location in world_obj.school_occupants
        )
        return school_nearby or not available_jobs

    def update_stressful_events(self):
        """Apply immediate and sustained mental-health costs from stressors."""
        current_events = set()
        if self.wealth < low_wealth_threshold:
            self.low_wealth_turns += 1
            if self.low_wealth_turns > low_wealth_stress_turns:
                current_events.add("low_wealth")
        else:
            self.low_wealth_turns = 0
        if self.hunger <= 0:
            current_events.add("hunger")

        for event in current_events:
            if event not in self.active_stressful_events:
                # A new stressful event has an immediate impact.
                self.mental_health = max(
                    0, self.mental_health - stress_mental_health_initial_drain
                )
            else:
                # The impact continues on every turn the event remains active.
                self.mental_health = max(
                    0, self.mental_health - stress_mental_health_sustained_drain
                )
        if not current_events:
            self.mental_health = min(
                100, self.mental_health + mental_health_recovery_per_turn
            )
        self.active_stressful_events = current_events

    def can_buy_food(self):
        return self.wealth >= grocery_food_cost and self.hunger < grocery_hunger_threshold

    def buy_house(self, world_obj, location):
        """Purchase an available house by paying its four-turn rent upfront."""
        house_type = world_obj.grid[location[0]][location[1]]
        if self.house is not None or house_type not in (6, 7):
            return False
        cost = 300 if house_type == 6 else 700
        if self.wealth < cost:
            return False
        self.wealth -= cost
        self.house = location
        self.house_turns_since_payment = 0
        world_obj.houses[location].add(self.id)
        event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                 "event": "bought", "house_type": house_type,
                 "position": location, "amount": cost, "wealth": self.wealth}
        world_obj.house_events.append(event)
        print("Agent {} bought a {} for ${:,} (wealth: ${:,}).".format(
            self.id, building_names[house_type], cost, self.wealth
        ))
        return True

    def advance_house_stay(self, world_obj):
        """Restore mood while housed and collect rent every four turns."""
        if self.house is None:
            return
        house_type = world_obj.grid[self.house[0]][self.house[1]]
        if (self.pos_x, self.pos_y) == self.house:
            self.mental_health = min(100, self.mental_health + (5 if house_type == 6 else 15))
        self.house_turns_since_payment += 1
        if self.house_turns_since_payment < 4:
            return
        cost = 300 if house_type == 6 else 700
        if self.wealth >= cost:
            self.wealth -= cost
            self.house_turns_since_payment = 0
            event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                     "event": "paid", "house_type": house_type,
                     "position": self.house, "amount": cost, "wealth": self.wealth}
            world_obj.house_events.append(event)
            print("Agent {} paid ${:,} rent for the {} (wealth: ${:,}).".format(
                self.id, cost, building_names[house_type], self.wealth
            ))
        else:
            location = self.house
            world_obj.houses[location].discard(self.id)
            self.house = None
            self.house_turns_since_payment = 0
            self.mental_health = max(0, self.mental_health - 25)
            event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                     "event": "evicted", "house_type": house_type,
                     "position": location, "amount": cost, "wealth": self.wealth,
                     "mental_health": self.mental_health}
            world_obj.house_events.append(event)
            print("Agent {} was evicted from the {}; lost 25 mental health (now {}).".format(
                self.id, building_names[house_type], self.mental_health
            ))

    def buy_food(self, world_obj, location):
        """Buy food at a grocery store and restore hunger, health, and mood."""
        if location not in world_obj.grocery_stores or not self.can_buy_food():
            return False
        if self.wealth < grocery_food_cost:
            print("Agent {} cannot afford food at the grocery store (cost: ${:,}; wealth: ${:,}).".format(
                self.id, grocery_food_cost, self.wealth
            ))
            return False

        self.wealth -= grocery_food_cost
        self.hunger = self.hunger_max
        self.health = min(health_max, self.health + grocery_food_health_restore)
        self.mental_health = min(100, self.mental_health + grocery_food_mental_restore)
        event = {
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "position": location,
            "cost": grocery_food_cost,
            "wealth": self.wealth,
            "health": self.health,
            "mental_health": self.mental_health,
            "hunger": self.hunger,
        }
        world_obj.grocery_events.append(event)
        if self.job == "Type 2 job":
            self.returning_to_job = True
        print("Agent {} bought food for ${:,} at the grocery store; hunger {}, health {}, mental health {}, wealth ${:,}.".format(
            self.id, grocery_food_cost, self.hunger, self.health,
            self.mental_health, self.wealth
        ))
        return True

    def advance_hospital_stay(self, world_obj):
        """Cure an admitted agent after one full turn in a hospital."""
        if self.hospitalized_at is None:
            return False
        self.hospital_stay_turns += 1
        if self.hospital_stay_turns < hospital_stay_duration_turns:
            return False

        cured_diseases = sorted(self.diseases)
        self.diseases.clear()
        if self.hospital_visit_event is not None:
            self.hospital_visit_event["cured_turn"] = world_obj.turnNo + 1
            self.hospital_visit_event["turns_in_hospital"] = self.hospital_stay_turns
            self.hospital_visit_event["outcome"] = "cured"
            self.hospital_visit_event = None
        self.hospitalized_at = None
        self.hospital_stay_turns = 0
        occupants = world_obj.hospital_occupants.get((self.pos_x, self.pos_y))
        if occupants is not None:
            occupants.discard(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == self.id:
                world_obj.agent_grid[self.pos_x][self.pos_y] = next(iter(occupants), 0)
        print("Agent {} completed one turn in the hospital and was cured of {}.".format(
            self.id, ", ".join(cured_diseases)
        ))
        return True

    def move(self, world_obj, rows=grid_rows, cols=grid_cols):
        if self.hospitalized_at is not None:
            print("Agent {} is staying in the hospital for treatment.".format(self.id))
            return None
        if (self.job == "Type 2 job" and not self.can_buy_food()
                and not self.diseases
                and not self.returning_to_job):
            print("Agent {} is staying at their type 2 job.".format(self.id))
            return None
        if (self.job == "Type 2 job" and self.returning_to_job
                and not self.diseases
                and (self.pos_x, self.pos_y) == self.employed_at):
            self.returning_to_job = False
            print("Agent {} returned to their type 2 job and is staying there.".format(self.id))
            return None
        if self.schooling_at is not None and not self.diseases:
            print("Agent {} is attending school ({}/5 turns).".format(
                self.id, self.school_turns
            ))
            return None

        # A resident stays home unless a health or food need sends them out.
        if (self.house is not None and (self.pos_x, self.pos_y) == self.house
                and not self.diseases and not self.can_buy_food()):
            return None

        visible_buildings = self.scan_surroundings(world_obj, rows, cols)
        job_targets = [
            location for location, job_holder in world_obj.building_jobs.items()
            if self.can_apply_for_type(world_obj.grid[location[0]][location[1]])
            and self.applied_buildings.get(location)
            != world_obj.job_opening_versions[location]
            and job_holder is None
        ]
        visible_empty = self.scan_empty_surroundings(world_obj, rows, cols)
        self.known_empty.update(visible_empty)
        self.known_empty.difference_update(visible_buildings)

        school_target = None
        if self.can_seek_school(world_obj):
            school_target = min(
                world_obj.school_occupants,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )

        grocery_target = None
        if self.can_buy_food():
            grocery_target = min(
                world_obj.grocery_stores,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )
            if (grocery_target == (self.pos_x, self.pos_y)
                    and not self.diseases):
                self.buy_food(world_obj, grocery_target)
                return None

        hospital_target = None
        if self.diseases:
            hospital_target = min(
                world_obj.hospitals,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )

        house_target = None
        if self.house is not None:
            house_target = self.house
        elif not self.diseases:
            affordable_houses = [
                location for location in world_obj.houses
                if self.wealth >= (300 if world_obj.grid[location[0]][location[1]] == 6 else 700)
            ]
            house_target = min(
                affordable_houses,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y), location
                ), default=None,
            )

        if hospital_target is not None:
            target_x, target_y = hospital_target
        elif grocery_target is not None:
            target_x, target_y = grocery_target
        elif self.job == "Type 2 job" and self.returning_to_job:
            target_x, target_y = self.employed_at
        elif school_target is not None:
            target_x, target_y = school_target
        elif job_targets:
            target_x, target_y = min(
                job_targets,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
            )
        elif house_target is not None:
            target_x, target_y = house_target
        else:
            target_x = target_y = None

        # A previously rejected agent may already be standing in a building
        # when its job reopens, so it can apply again without walking out and back in.
        if school_target == (self.pos_x, self.pos_y):
            self.start_school(world_obj, school_target)
            return None

        if (target_x, target_y) == (self.pos_x, self.pos_y):
            if (self.house is None
                    and world_obj.grid[self.pos_x][self.pos_y] in (6, 7)):
                self.buy_house(world_obj, (self.pos_x, self.pos_y))
                if self.house is not None:
                    return None
            self.apply_for_job(
                world_obj,
                world_obj.grid[self.pos_x][self.pos_y],
                (self.pos_x, self.pos_y),
            )
            job_targets = [
                location for location, job_holder in world_obj.building_jobs.items()
                if self.can_apply_for_type(world_obj.grid[location[0]][location[1]])
                and self.applied_buildings.get(location)
                != world_obj.job_opening_versions[location]
                and job_holder is None
            ]
            if self.job == "Type 2 job":
                return None
            if job_targets:
                target_x, target_y = min(
                    job_targets,
                    key=lambda location: (
                        abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                        location,
                    ),
                )
            else:
                target_x = target_y = None

        preferred_moves = []
        if target_x is not None:
            step_x = 1 if target_x > self.pos_x else (-1 if target_x < self.pos_x else 0)
            step_y = 1 if target_y > self.pos_y else (-1 if target_y < self.pos_y else 0)

            if step_x != 0 and step_y != 0:
                preferred_moves = [(step_x, 0), (0, step_y)]
            else:
                preferred_moves = [(step_x, step_y)]
            if (target_x, target_y) in visible_buildings:
                print("Agent {} spotted a {} at ({}, {}).".format(
                    self.id, building_names[world_obj.grid[target_x][target_y]], target_x, target_y
                ))

        possible_moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        unexplored_moves = []
        new_position_moves = []
        legal_preferred_moves = []
        fallback_moves = []
        blocked_moves = []
        move_destinations = {}
        for move_x, move_y in possible_moves:
            next_x = max(0, min(rows - 1, self.pos_x + move_x))
            next_y = max(0, min(cols - 1, self.pos_y + move_y))
            move = (move_x, move_y)
            destination = (next_x, next_y)
            if destination == (self.pos_x, self.pos_y):
                continue
            if world_obj.grid[next_x][next_y] == 5 and not self.diseases:
                continue
            if (world_obj.agent_grid[next_x][next_y] not in (0, self.id)
                    and world_obj.grid[next_x][next_y] not in (3, 4, 5, 6, 7)):
                blocked_moves.append(move)
                continue
            fallback_moves.append(move)
            move_destinations[move] = destination
            if destination not in self.known_empty:
                unexplored_moves.append(move)
            if destination not in self.visited_positions:
                new_position_moves.append(move)
            if move in preferred_moves:
                legal_preferred_moves.append(move)

        # Explore locations with unknown building status first, then locations
        # this agent has not physically visited. Revisit old locations only
        # when needed, preferring the least-visited route.
        if legal_preferred_moves:
            dx, dy = random.choice(legal_preferred_moves)
        elif target_x is not None and fallback_moves:
            current_distance = abs(target_x - self.pos_x) + abs(target_y - self.pos_y)
            progress_moves = [
                move for move in fallback_moves
                if abs(move_destinations[move][0] - target_x)
                + abs(move_destinations[move][1] - target_y) < current_distance
            ]
            if progress_moves:
                best_distance = min(
                    abs(move_destinations[move][0] - target_x)
                    + abs(move_destinations[move][1] - target_y)
                    for move in progress_moves
                )
                best_moves = [
                    move for move in progress_moves
                    if abs(move_destinations[move][0] - target_x)
                    + abs(move_destinations[move][1] - target_y) == best_distance
                ]
                dx, dy = random.choice(best_moves)
            elif unexplored_moves:
                dx, dy = random.choice(unexplored_moves)
            elif new_position_moves:
                dx, dy = random.choice(new_position_moves)
            else:
                dx, dy = random.choice(fallback_moves)
        elif unexplored_moves:
            dx, dy = random.choice(unexplored_moves)
        elif new_position_moves:
            dx, dy = random.choice(new_position_moves)
        elif fallback_moves:
            alternatives = [
                move for move in fallback_moves
                if move_destinations[move] != self.previous_position
            ]
            if not alternatives:
                alternatives = fallback_moves
            least_visited_count = min(
                self.position_visits.get(move_destinations[move], 0)
                for move in alternatives
            )
            least_visited_moves = [
                move for move in alternatives
                if self.position_visits.get(move_destinations[move], 0) == least_visited_count
            ]
            dx, dy = random.choice(least_visited_moves)
        elif blocked_moves:
            # Only attempt a blocked move if every available direction is occupied.
            # This preserves collision-based information sharing without trapping agents
            # beside a stationary type 2 employee when other routes are open.
            dx, dy = random.choice(blocked_moves)
        else:
            dx = dy = 0

        next_x = max(0, min(rows-1, self.pos_x + dx))
        next_y = max(0, min(cols-1, self.pos_y + dy))
        other_agent_id = world_obj.agent_grid[next_x][next_y]
        if (other_agent_id not in (0, self.id)
                and world_obj.grid[next_x][next_y] not in (3, 4, 5, 6, 7)):
            print("Agent {} bumped into Agent {} at ({}, {}).".format(
                self.id, other_agent_id, next_x, next_y
            ))
            return other_agent_id

        old_position = (self.pos_x, self.pos_y)
        old_shared_occupants = world_obj.school_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.grocery_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.hospital_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.houses.get(old_position)
        if old_shared_occupants is not None:
            old_shared_occupants.discard(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == self.id:
                world_obj.agent_grid[self.pos_x][self.pos_y] = (
                    next(iter(old_shared_occupants)) if old_shared_occupants else 0
                )
        else:
            world_obj.agent_grid[self.pos_x][self.pos_y] = 0
        self.pos_x, self.pos_y = next_x, next_y
        if self.diseases and self.schooling_at is not None:
            self.schooling_at = None
            self.school_turns = 0
        if (self.job == "Type 2 job" and self.returning_to_job
                and (self.pos_x, self.pos_y) == self.employed_at):
            self.returning_to_job = False
        self.previous_position = old_position
        new_position = (self.pos_x, self.pos_y)
        self.visited_positions.add(new_position)
        self.position_visits[new_position] = self.position_visits.get(new_position, 0) + 1

        building_location = (self.pos_x, self.pos_y)
        if world_obj.grid[self.pos_x][self.pos_y] in (3, 4, 5, 6, 7):
            occupants = world_obj.school_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.grocery_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.hospital_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.houses.get(building_location)
            occupants.add(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == 0:
                world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        else:
            world_obj.agent_grid[self.pos_x][self.pos_y] = self.id

        print("Agent {} moved to ({}, {})".format(self.id, self.pos_x, self.pos_y))
        
        building_type = world_obj.grid[self.pos_x][self.pos_y]
        if building_type and old_position != building_location:
            world_obj.building_entries.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "building_type": building_type,
                "position": building_location,
            })
            print("Agent {} entered the {} at ({}, {}).".format(
                self.id, building_names[building_type], self.pos_x, self.pos_y
            ))
            if building_type in (1, 2):
                self.apply_for_job(world_obj, building_type, building_location)
            elif building_type == 3 and school_target == building_location:
                self.start_school(world_obj, building_location)
            elif building_type == 4:
                self.buy_food(world_obj, building_location)
            elif building_type == 5 and self.diseases:
                self.hospitalized_at = building_location
                self.hospital_stay_turns = 0
                self.hospital_visit_event = {
                    "admitted_turn": world_obj.turnNo + 1,
                    "agent_id": self.id,
                    "position": building_location,
                    "diseases": sorted(self.diseases),
                    "cured_turn": None,
                    "turns_in_hospital": None,
                    "outcome": "in treatment",
                }
                world_obj.hospital_events.append(self.hospital_visit_event)
                if self.job == "Type 2 job":
                    self.returning_to_job = True
                print("Agent {} entered the hospital with {}; treatment takes one turn.".format(
                    self.id, ", ".join(sorted(self.diseases))
                ))
            elif building_type in (6, 7):
                if self.house == building_location:
                    return None
                self.buy_house(world_obj, building_location)

    def start_school(self, world_obj, location):
        """Enroll the agent at a school; multiple agents may share its tile."""
        if self.job is not None or self.school_completed or self.schooling_at is not None:
            return False
        self.schooling_at = location
        self.school_turns = 0
        world_obj.school_occupants[location].add(self.id)
        world_obj.school_events.append({
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "event": "enrolled",
            "position": location,
        })
        print("Agent {} enrolled in school at ({}, {}).".format(
            self.id, location[0], location[1]
        ))
        return True

    def can_apply_for_type(self, building_type):
        """Unemployed agents can apply anywhere; type 1 employees seek type 2."""
        if self.job is None:
            return True
        return self.job == "Type 1 job" and building_type == 2

    def apply_for_job(self, world_obj, building_type, building_location):
        """Apply once per opening using intelligence, willpower and health."""
        if not self.can_apply_for_type(building_type):
            return False
        opening_version = world_obj.job_opening_versions[building_location]
        if self.applied_buildings.get(building_location) == opening_version:
            return False
        self.applied_buildings[building_location] = opening_version
        if world_obj.building_jobs[building_location] is not None:
            print("Agent {} found no open job at this building.".format(self.id))
            return False

        intelligence_score = max(0, min(100, (self.intelligence - 40) * 100 / 105))
        health_range = health_max - health_min
        health_score = (
            (self.health - health_min) * 100 / health_range if health_range else 100
        )
        weights = {
            "intelligence": 1.2,
            "willpower": 1.0,
            "mental_health": 0.8,
            "health": 0.8,
        }
        weighted_total = (
            intelligence_score * weights["intelligence"]
            + self.willpower * weights["willpower"]
            + self.mental_health * weights["mental_health"]
            + health_score * weights["health"]
        )
        application_score = weighted_total / sum(weights.values())
        # Keep type 1 reachable for an otherwise average agent; type 2 is
        # harder, while allowing above-average intelligence to qualify with
        # typical willpower and health.
        minimum_score = {1: 60, 2: 73}[building_type]
        hired = application_score >= minimum_score
        job_title = "Type {} job".format(building_type)
        event = {
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "building_type": building_type,
            "position": building_location,
            "score": round(application_score, 1),
            "minimum_score": minimum_score,
            "hired": hired,
            "job": job_title,
        }
        world_obj.job_application_events.append(event)
        if hired:
            previous_job = self.job
            previous_location = self.employed_at
            if previous_job is not None:
                world_obj.reopen_job(previous_location, self)
            world_obj.building_jobs[building_location] = self.id
            self.job = job_title
            self.employed_at = building_location
            world_obj.hiring_events.append(event.copy())
            print("Agent {} successfully got the {} at the {}!".format(
                self.id, job_title, building_names[building_type]
            ))
        else:
            print("Agent {} was not hired for the {} (score: {}; required: {}); "
                  "they will look for another eligible building.".format(
                self.id, job_title, event["score"], minimum_score
            ))
        return hired
