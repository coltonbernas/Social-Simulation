import random

try:
    from .config import (
        grid_rows, grid_cols, health_min, health_max,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn, hunger_drain_per_step,
    )
except ImportError:
    from config import (
        grid_rows, grid_cols, health_min, health_max,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn, hunger_drain_per_step,
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
        self.age = random.randint(1, 30) if age is None else age
        self.death_age = random.randint(80, 100)
        self.intelligence = random_intelligence()
        # A simple physical-health score. Healthy agents tend toward 100;
        # age and active disease lower the score over time.
        starting_health_min = min(70, health_max)
        self.health = max(
            health_min,
            min(health_max, random.randint(starting_health_min, health_max) - max(0, self.age - 60)),
        )
        self.diseases = set()
        #Gonna make this affect hard decisions and getting a job
        self.willpower = random.randint(0, 100)
        self.mental_health = 100
        self.wealth = None
        self.job = None
        self.employed_at = None
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
        self.personality_type = None
        self.inheritance = None
        self.genes = []
        self.religion = None
        self.education = None
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

        world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        print("Agent {} spawned at ({},{}); age: {}; natural death age: {}; "
              "intelligence: {}; willpower: {}".format(
            self.id, self.pos_x, self.pos_y, self.age, self.death_age,
            self.intelligence, self.willpower
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
        self.health = max(health_min, self.health - disease_health_impact)
        return True

    def update_health(self, world_obj=None):
        """Apply health changes, including starvation and stressful events."""
        self.hunger = max(0, self.hunger - hunger_drain_per_step)
        if not self.diseases and random.random() < disease_chance_per_turn:
            disease = "common_cold"
            self.diseases.add(disease)
            self.health = max(health_min, self.health - disease_health_impact)
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
            self.health = max(health_min, self.health - 1)
        else:
            self.health = min(health_max, self.health + 1)

        if self.hunger <= 0:
            self.health = max(health_min, self.health - 2)

        self.update_stressful_events()

    def update_stressful_events(self):
        """Apply immediate and sustained mental-health costs from stressors."""
        current_events = set()
        if isinstance(self.wealth, (int, float)):
            if self.wealth <= 0:
                current_events.add("no_wealth")
            elif self.wealth <= 10:
                current_events.add("low_wealth")
        if self.hunger <= 0:
            current_events.add("hunger")

        for event in current_events:
            if event not in self.active_stressful_events:
                # A new stressful event has an immediate impact.
                self.mental_health = max(0, self.mental_health - 5)
            else:
                # The impact continues on every turn the event remains active.
                self.mental_health = max(0, self.mental_health - 2)
        self.active_stressful_events = current_events

    def move(self, world_obj, rows=grid_rows, cols=grid_cols):
        if self.job == "Type 2 job":
            print("Agent {} is staying at their type 2 job.".format(self.id))
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

        # A previously rejected agent may already be standing in a building
        # when its job reopens, so it can apply again without walking out and back in.
        if (target_x, target_y) == (self.pos_x, self.pos_y):
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
                print("Agent {} spotted a type {} building at ({}, {}).".format(
                    self.id, world_obj.grid[target_x][target_y], target_x, target_y
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
            if world_obj.agent_grid[next_x][next_y] not in (0, self.id):
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
        if other_agent_id not in (0, self.id):
            print("Agent {} bumped into Agent {} at ({}, {}).".format(
                self.id, other_agent_id, next_x, next_y
            ))
            return other_agent_id

        old_position = (self.pos_x, self.pos_y)
        world_obj.agent_grid[self.pos_x][self.pos_y] = 0
        self.pos_x, self.pos_y = next_x, next_y
        self.previous_position = old_position
        new_position = (self.pos_x, self.pos_y)
        self.visited_positions.add(new_position)
        self.position_visits[new_position] = self.position_visits.get(new_position, 0) + 1

        world_obj.agent_grid[self.pos_x][self.pos_y] = self.id

        print("Agent {} moved to ({}, {})".format(self.id, self.pos_x, self.pos_y))
        
        building_type = world_obj.grid[self.pos_x][self.pos_y]
        building_location = (self.pos_x, self.pos_y)
        if building_type and old_position != building_location:
            world_obj.building_entries.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "building_type": building_type,
                "position": building_location,
            })
            print("Agent {} entered type {} building at ({}, {}).".format(
                self.id, building_type, self.pos_x, self.pos_y
            ))
            self.apply_for_job(world_obj, building_type, building_location)

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
        application_score = (
            intelligence_score + self.willpower + self.mental_health + health_score
        ) / 4
        minimum_score = {1: 60, 2: 75}[building_type]
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
            print("Agent {} successfully got the {} at the type {} building!".format(
                self.id, job_title, building_type
            ))
        else:
            print("Agent {} was not hired for the {} (score: {}; required: {}); "
                  "they will look for another eligible building.".format(
                self.id, job_title, event["score"], minimum_score
            ))
        return hired
