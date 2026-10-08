try:
    from .agent import Agent
    from .config import agent_count
except ImportError:
    from agent import Agent
    from config import agent_count


class Population:
    def __init__(self, world_obj, count=agent_count):
        self.agents = [Agent(agent_id=i, world_obj=world_obj) for i in range(count)]

    def share_information(self, first, second, world_obj):
        """Exchange known empty locations after two agents collide."""
        first_locations = tuple(sorted(first.known_empty))
        second_locations = tuple(sorted(second.known_empty))

        first.receive_message(second_locations)
        second.receive_message(first_locations)

        world_obj.communication_events.extend((
            {
                "turn": world_obj.turnNo + 1,
                "sender_id": first.id,
                "receiver_id": second.id,
                "empty_locations": first_locations,
            },
            {
                "turn": world_obj.turnNo + 1,
                "sender_id": second.id,
                "receiver_id": first.id,
                "empty_locations": second_locations,
            },
        ))
        print("Agents {} and {} exchanged {} and {} known empty location(s).".format(
            first.id, second.id, len(first_locations), len(second_locations)
        ))

    def step_agents(self, world_obj):
        # Agents exchange information only when a move is blocked by another
        # agent occupying the destination cell.
        agents_by_id = {agent.id: agent for agent in self.agents}
        for agent in self.agents:
            other_agent_id = agent.move(world_obj)
            if other_agent_id is not None:
                self.share_information(agent, agents_by_id[other_agent_id], world_obj)
        world_obj.turnNo +=1

    def print_stat_card(self, world_obj):
        """Print the final collection and communication history."""
        pickup_counts = {agent.id: 0 for agent in self.agents}
        for event in world_obj.pickup_events:
            pickup_counts[event["agent_id"]] += 1

        print("\n" + "=" * 58)
        print("POST-GAME STAT CARD")
        print("=" * 58)
        print("Turns completed: {}".format(world_obj.turnNo))
        print("Fruit collected: {} / {}".format(
            len(world_obj.pickup_events),
            len(world_obj.pickup_events) + world_obj.fruit,
        ))

        print("\nFruit pickups (in order):")
        if world_obj.pickup_events:
            for order, event in enumerate(world_obj.pickup_events, start=1):
                x, y = event["position"]
                print("  {}. Turn {}: Agent {} picked fruit at ({}, {})".format(
                    order, event["turn"], event["agent_id"], x, y
                ))
        else:
            print("  No fruit was collected.")

        print("\nAgent totals:")
        for agent_id, count in pickup_counts.items():
            print("  Agent {}: {} fruit".format(agent_id, count))

        print("\nCommunications:")
        if world_obj.communication_events:
            for event in world_obj.communication_events:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: Agent {} told Agent {} these fruit-free places: {}".format(
                    event["turn"], event["sender_id"], event["receiver_id"], locations
                ))
        else:
            print("  No messages were exchanged.")
        print("=" * 58)

    def print_batch_report(self, world_obj, start_turn, end_turn):
        """Print events produced during one batch of turns."""
        pickups = [
            event for event in world_obj.pickup_events
            if start_turn <= event["turn"] <= end_turn
        ]
        communications = [
            event for event in world_obj.communication_events
            if start_turn <= event["turn"] <= end_turn
        ]
        pickup_counts = {agent.id: 0 for agent in self.agents}
        for event in pickups:
            pickup_counts[event["agent_id"]] += 1

        print("\n" + "-" * 58)
        print("BATCH REPORT: Turns {}-{}".format(start_turn, end_turn))
        print("Fruit collected: {}".format(len(pickups)))
        print("Pickups:")
        if pickups:
            for event in pickups:
                x, y = event["position"]
                print("  Turn {}: Agent {} picked fruit at ({}, {})".format(
                    event["turn"], event["agent_id"], x, y
                ))
        else:
            print("  None")

        print("Agent totals for this batch:")
        for agent_id, count in pickup_counts.items():
            print("  Agent {}: {} fruit".format(agent_id, count))

        print("Communications:")
        if communications:
            for event in communications:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: Agent {} told Agent {} these fruit-free places: {}".format(
                    event["turn"], event["sender_id"], event["receiver_id"], locations
                ))
        else:
            print("  None")
        print("Fruit remaining: {}".format(world_obj.fruit))
        print("-" * 58)
