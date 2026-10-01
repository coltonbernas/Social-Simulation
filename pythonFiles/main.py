import time

from world import World
from population import Population

def main():
    world_obj = World()
    pop = Population(world_obj=world_obj)

    print(f"World created with {world_obj.rows} rows and {world_obj .cols} columns, placed {len(pop.agents)} agents.")

    while True:
        time.sleep(3)
        print("Turn {}:".format(world_obj.turnNo))
        pop.step_agents(world_obj)

        print()



if __name__ == "__main__":
    main()