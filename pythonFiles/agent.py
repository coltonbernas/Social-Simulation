import random

from pythonFiles.config import grid_rows, grid_cols


class Agent:
    def __init__(self, agent_id, world_obj, rows=grid_rows, cols=grid_cols):
        self.id = agent_id+1
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
            self.known_empty.add((self.pos_x, self.pos_y))
            world_obj.pickup_events.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "position": (self.pos_x, self.pos_y),
            })
            print ("Agent {} picked up a fruit. {} fruit remain.".format(self.id, world_obj.fruit))
            world_obj.grid[self.pos_x][self.pos_y] = 0
