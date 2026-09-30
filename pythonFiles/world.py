import string
import math
import random


rows = 15
cols = 15

fruit = 4

gridArray = [[0 for _ in range(rows)] for _ in range(cols)]

placed = 0

for i in range(fruit):
    while placed < fruit:
        posx = random.randint(0,cols-1)
        posy = random.randint(0,rows-1)

        if gridArray[posx][posy] == 0:
            gridArray[posx][posy] = 1
            placed += 1

for i in range(rows):
    for j in range(cols):
        print(gridArray[i][j], end=" ")
    print()