import random
from config import grid_rows, grid_cols, fruit_count

class World:
    def __init__(self, rows=grid_rows, cols=grid_cols, fruit=fruit_count):
        self.fruit = fruit
        self.rows = rows
        self.cols = cols
        self.grid = [[0 for _ in range(rows)] for _ in range(cols)]
        self.agent_grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.pickup_events = []
        self.communication_events = []
        self.place_fruit(fruit)
        self.turnNo = 0


    def place_fruit(self, count):
        placed = 0
        while placed < count:
            posx = random.randint(0,self.cols-1)
            posy = random.randint(0,self.rows-1)

            if self.grid[posx][posy] == 0:
                self.grid[posx][posy] = 1
                placed += 1

        for i in range(self.rows):
            for j in range(self.cols):
                print(self.grid[i][j], end=" ")
            print()
