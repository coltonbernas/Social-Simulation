import time

from world import World
from population import Population

def main():
    world = World()
    pop = Population()

    print(f"World created with {world.rows} rows and {world.cols} columns, placed {len(pop.agents)} agents.")

    while True:
        time.sleep(3)
        print("Turn {}:".format(world.turnNo))
        pop.step_agents(world)

        print()



if __name__ == "__main__":
    main()