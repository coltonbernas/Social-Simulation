import time

from world import World
from population import Population

def main():
    world_obj = World()
    pop = Population(world_obj=world_obj)

    max_turns = 10000

    print(f"World created with {world_obj.rows} rows and {world_obj .cols} columns, placed {len(pop.agents)} agents.")

    for turn in range(1, max_turns + 1):
        if world_obj.fruit == 0:
            print(f"All fruit picked up simulation done")
            break

        time.sleep(1)
        print("Turn {}:".format(world_obj.turnNo))
        pop.step_agents(world_obj)
        print()





if __name__ == "__main__":
    main()