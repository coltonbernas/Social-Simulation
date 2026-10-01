import string
import math
import random
import world

from pythonFiles.config import grid_rows, grid_cols


class Agent:
    def __init__(self, agent_id, world_obj,  rows=grid_rows, cols=grid_rows):
        self.id = agent_id+1
        self.pos_x, self.pos_y  = self.get_safe_spawn_pos(world_obj, rows, cols)

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



    def move(self, world_obj, rows=grid_rows, cols=grid_rows):

        dx, dy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])

        self.pos_x = max(0, min(rows-1, self.pos_x + dx))
        self.pos_y = max(0, min(cols-1, self.pos_y + dy))

        print("Agent {} moved to ({}, {})".format(self.id, self.pos_x, self.pos_y))
        
        if world_obj.grid[self.pos_x][self.pos_y] == 1:
            world_obj.fruit-=1
            print ("Agent {} picked up a fruit. {} fruit remain.".format(self.id, world_obj.fruit))
            world_obj.grid[self.pos_x][self.pos_y] = 0
            