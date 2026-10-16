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

    print(f"World created with {world_obj.rows} rows and {world_obj .cols} columns, placed {len(pop.agents)} agents.")

    manually_ended = False
    try:
        while pop.agents:
            batch_size = get_batch_size()
            batch_start = world_obj.turnNo + 1

            for _ in range(batch_size):
                if not pop.agents:
                    break
                time.sleep(1)
                print("Turn {}:".format(world_obj.turnNo + 1))
                pop.step_agents(world_obj)
                print()

            pop.print_batch_report(world_obj, batch_start, world_obj.turnNo)
    except KeyboardInterrupt:
        manually_ended = True
        print("\nSimulation ended manually.")
    finally:
        if not manually_ended and not pop.agents:
            print("All agents have died; simulation done.")

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
