import sys
import time

try:
    from .world import World
    from .population import Population
except ImportError:
    from world import World
    from population import Population


def get_batch_size():
    while True:
        answer = input("Steps for next batch [10]: ").strip()
        if not answer:
            return 10
        try:
            batch_size = int(answer)
        except ValueError:
            print("Enter a whole number greater than zero.")
            continue
        if batch_size > 0:
            return batch_size
        print("Enter a whole number greater than zero.")


def main():
    world_obj = World()
    pop = Population(world_obj=world_obj)

    max_turns = 10000

    print(f"World created with {world_obj.rows} rows and {world_obj .cols} columns, placed {len(pop.agents)} agents.")

    while world_obj.turnNo < max_turns and world_obj.fruit > 0:
        batch_size = get_batch_size()
        batch_start = world_obj.turnNo + 1
        steps_this_batch = min(batch_size, max_turns - world_obj.turnNo)

        for _ in range(steps_this_batch):
            if world_obj.fruit == 0:
                break
            time.sleep(1)
            print("Turn {}:".format(world_obj.turnNo + 1))
            pop.step_agents(world_obj)
            print()

        pop.print_batch_report(world_obj, batch_start, world_obj.turnNo)

    if world_obj.fruit == 0:
        print("All fruit picked up; simulation done.")
    elif world_obj.turnNo == max_turns:
        print("Reached the {} turn limit.".format(max_turns))

    pop.print_stat_card(world_obj)

if __name__ == "__main__":
    if "--console" in sys.argv:
        main()
    else:
        try:
            from .popout import launch
        except ImportError:
            from popout import launch
        launch()
