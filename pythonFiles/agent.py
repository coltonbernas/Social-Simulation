import random

try:
    from .config import (
        grid_rows, grid_cols, health_min, health_max,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn,
    )
except ImportError:
    from config import (
        grid_rows, grid_cols, health_min, health_max,
        base_disease_transmission, disease_health_impact,
        disease_chance_per_turn,
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
        self.age = random.randint(1, 80) if age is None else age
        self.intelligence = random_intelligence()
        # A simple physical-health score. Healthy agents tend toward 100;
        # age and active disease lower the score over time.
        starting_health_min = min(70, health_max)
        self.health = max(
            health_min,
            min(health_max, random.randint(starting_health_min, health_max) - max(0, self.age - 60)),
        )
        self.diseases = set()
        self.willpower = None
        self.mental_health = None
        self.wealth = None
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
        # Cells observed or reported to contain no fruit.
        self.known_empty = set()
        self.visited_positions = {(self.pos_x, self.pos_y)}
        self.position_visits = {(self.pos_x, self.pos_y): 1}
        self.previous_position = None

        world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        print("Agent {} spawned at ({},{})".format(self.id, self.pos_x, self.pos_y))

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
                    if world_obj.grid[nx][ny] == 1:
                            return False
                    if world_obj.agent_grid[nx][ny] != 0:
                        return False
        return True

    def scan_surroundings(self, world_obj, rows, cols):
        visible_fruits = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = self.pos_x + dx, self.pos_y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] == 1:
                        visible_fruits.append((nx, ny))
        return visible_fruits

    def scan_empty_surroundings(self, world_obj, rows, cols):
        """Return nearby cells that do not contain fruit."""
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
        """Remember cells another agent reports as empty of fruit."""
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
        """Apply health changes and check for naturally acquired disease."""
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

    def heal_from_fruit(self):
        """Clear all diseases when the agent collects a fruit; return them."""
        healed_diseases = tuple(sorted(self.diseases))
        self.diseases.clear()
        return healed_diseases

    def move(self, world_obj, rows=grid_rows, cols=grid_cols):
        visible_fruits = self.scan_surroundings(world_obj, rows, cols)
        visible_empty = self.scan_empty_surroundings(world_obj, rows, cols)
        self.known_empty.update(visible_empty)
        self.known_empty.difference_update(visible_fruits)

        if visible_fruits:
            target_x, target_y = visible_fruits[0]
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
            if (target_x, target_y) in visible_fruits:
                print("Agent {} spotted a fruit at ({},{})!".format(self.id, target_x, target_y))

        possible_moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        unexplored_moves = []
        new_position_moves = []
        legal_preferred_moves = []
        fallback_moves = []
        move_destinations = {}
        for move_x, move_y in possible_moves:
            next_x = max(0, min(rows - 1, self.pos_x + move_x))
            next_y = max(0, min(cols - 1, self.pos_y + move_y))
            move = (move_x, move_y)
            destination = (next_x, next_y)
            if destination == (self.pos_x, self.pos_y):
                continue
            fallback_moves.append(move)
            move_destinations[move] = destination
            if destination not in self.known_empty:
                unexplored_moves.append(move)
            if destination not in self.visited_positions:
                new_position_moves.append(move)
            if move in preferred_moves:
                legal_preferred_moves.append(move)

        # Explore locations with unknown fruit status first, then locations
        # this agent has not physically visited. Revisit old locations only
        # when needed, preferring the least-visited route.
        if legal_preferred_moves:
            dx, dy = random.choice(legal_preferred_moves)
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
        
        if world_obj.grid[self.pos_x][self.pos_y] == 1:
            world_obj.fruit-=1
            healed_diseases = self.heal_from_fruit()
            if healed_diseases:
                world_obj.disease_events.append({
                    "turn": world_obj.turnNo + 1,
                    "agent_id": self.id,
                    "recovered_from": healed_diseases,
                    "health": self.health,
                })
                print("Agent {} recovered from {} after collecting fruit.".format(
                    self.id, ", ".join(healed_diseases)
                ))
            self.known_empty.add((self.pos_x, self.pos_y))
            world_obj.pickup_events.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "position": (self.pos_x, self.pos_y),
            })
            print ("Agent {} picked up a fruit. {} fruit remain.".format(self.id, world_obj.fruit))
            world_obj.grid[self.pos_x][self.pos_y] = 0
