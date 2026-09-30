import string
import math
import random
import world

from pythonFiles.config import grid_rows


class Agent:
    def __init__(self, agent_id, rows=grid_rows, cols=grid_rows):
        self.id = agent_id+1
        self.pos_x = random.randint(0, rows - 1)
        self.pos_y = random.randint(0, cols - 1)
        print("Agent {} spawned at ({},{})".format(self.id, self.pos_x, self.pos_y))

    def move(self, world_obj, rows=grid_rows, cols=grid_rows):

        dx, dy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])

        self.pos_x = max(0, min(rows-1, self.pos_x + dx))
        self.pos_y = max(0, min(cols-1, self.pos_y + dy))

        print("Agent {} moved to ({}, {})".format(self.id, self.pos_x, self.pos_y))
        
        if world_obj.grid[self.pos_x][self.pos_y] == 1:
            world_obj.fruit-=1
            print ("Agent {} picked up a fruit. {} fruit remain.".format(self.id, world_obj.fruit))
            world_obj.grid[self.pos_x][self.pos_y] = 0
            