try:
    from .agent import Agent
    from .config import agent_count
except ImportError:
    from agent import Agent
    from config import agent_count


class Population:
    def __init__(self, world_obj, count=agent_count):
        self.agents = [Agent(agent_id=i, world_obj=world_obj) for i in range(count)]
        self.all_agents = list(self.agents)
        self.next_agent_id = count

    def birth(self, world_obj):
        """Create and add a newborn agent whose age is exactly 1."""
        newborn = Agent(
            agent_id=self.next_agent_id,
            world_obj=world_obj,
            age=1,
        )
        self.next_agent_id += 1
        self.agents.append(newborn)
        self.all_agents.append(newborn)
        return newborn

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

        # A blocked move represents close contact. Either infectious agent
        # may transmit to the other, with risk adjusted for the recipient's health.
        self._try_transmission(first, second, world_obj)
        self._try_transmission(second, first, world_obj)

    @staticmethod
    def _try_transmission(source, target, world_obj):
        if not source.diseases:
            return
        disease = sorted(source.diseases)[0]
        if target.catch_disease(disease):
            world_obj.disease_events.append({
                "turn": world_obj.turnNo + 1,
                "source_id": source.id,
                "agent_id": target.id,
                "disease": disease,
                "health": target.health,
            })
            print("Agent {} caught {} from Agent {} (health: {}).".format(
                target.id, disease, source.id, target.health
            ))

    def step_agents(self, world_obj):
        # One simulation turn represents one year of aging.
        for agent in list(self.agents):
            if agent.age < agent.death_age:
                agent.age += 1
            if agent.age >= agent.death_age:
                self._remove_agent(agent, world_obj, "old age")

        # Agents exchange information only when a move is blocked by another
        # agent occupying the destination cell.
        agents_by_id = {agent.id: agent for agent in self.agents}
        for agent in self.agents:
            other_agent_id = agent.move(world_obj)
            if other_agent_id is not None:
                self.share_information(agent, agents_by_id[other_agent_id], world_obj)
        for agent in list(self.agents):
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
                continue
            agent.update_health(world_obj)
            if agent.health <= 0:
                self._remove_agent(agent, world_obj, "zero health")
            else:
                agent.advance_school(world_obj)
        world_obj.turnNo +=1

    def _remove_agent(self, agent, world_obj, cause):
        """Remove a dead agent and reopen any job they held."""
        if cause == "zero health":
            cause = agent.last_health_damage_cause or "unknown cause"
        if agent.job is not None:
            world_obj.reopen_job(
                agent.employed_at, agent, reason="died from {}".format(cause)
            )
        location = (agent.pos_x, agent.pos_y)
        school_occupants = world_obj.school_occupants.get(location)
        if school_occupants is not None:
            school_occupants.discard(agent.id)
            if world_obj.agent_grid[agent.pos_x][agent.pos_y] == agent.id:
                world_obj.agent_grid[agent.pos_x][agent.pos_y] = (
                    next(iter(school_occupants)) if school_occupants else 0
                )
        else:
            world_obj.agent_grid[agent.pos_x][agent.pos_y] = 0
        world_obj.death_events.append({
            "turn": world_obj.turnNo + 1,
            "agent_id": agent.id,
            "age": agent.age,
            "cause": cause,
        })
        self.agents.remove(agent)
        print("Agent {} died from {} at age {}.".format(agent.id, cause, agent.age))

    def print_stat_card(self, world_obj):
        """Print the final building, employment and communication history."""
        print("\n" + "=" * 58)
        print("POST-GAME STAT CARD")
        print("=" * 58)
        print("Turns completed: {}".format(world_obj.turnNo))
        print("Buildings: {} ({} open jobs)".format(
            world_obj.building_count, world_obj.open_jobs
        ))

        deaths_by_agent = {
            event["agent_id"]: event for event in world_obj.death_events
        }
        print("\nAgent outcomes:")
        for agent in self.all_agents:
            death = deaths_by_agent.get(agent.id)
            if death:
                print("  Agent {}: DIED at age {} (cause: {}); end intelligence: {}".format(
                    agent.id, death["age"], death["cause"], agent.intelligence
                ))
            else:
                print("  Agent {}: alive; end intelligence: {}".format(
                    agent.id, agent.intelligence
                ))

        print("\nHiring history:")
        if world_obj.hiring_events:
            for event in world_obj.hiring_events:
                x, y = event["position"]
                print("  Turn {}: Agent {} got the {} in type {} building at ({}, {})".format(
                    event["turn"], event["agent_id"], event["job"],
                    event["building_type"], x, y
                ))
        else:
            print("  No agents were hired.")

        rejections = [
            event for event in world_obj.job_application_events
            if not event["hired"]
        ]
        print("\nRejected job applications:")
        if rejections:
            for event in rejections:
                x, y = event["position"]
                print("  Turn {}: Agent {} was rejected from the {} at type {} building "
                      "({}, {}) (score: {}; required: {}).".format(
                    event["turn"], event["agent_id"], event["job"],
                    event["building_type"], x, y,
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("\nDisease history:")
        if world_obj.disease_events:
            for event in world_obj.disease_events:
                if event.get("source") == "natural":
                    print("  Turn {}: Agent {} contracted {} naturally".format(
                        event["turn"], event["agent_id"], event["disease"]
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], event["disease"],
                        event["source_id"]
                    ))
        else:
            print("  None")

        print("\nSchool history:")
        if world_obj.school_events:
            for event in world_obj.school_events:
                if event["event"] == "enrolled":
                    x, y = event["position"]
                    print("  Turn {}: Agent {} enrolled at ({}, {})".format(
                        event["turn"], event["agent_id"], x, y
                    ))
                else:
                    print("  Turn {}: Agent {} graduated; intelligence is now {}".format(
                        event["turn"], event["agent_id"], event["intelligence"]
                    ))
        else:
            print("  None")

        print("\nJob upgrades and vacancies:")
        if world_obj.job_quit_events:
            for event in world_obj.job_quit_events:
                x, y = event["position"]
                print("  Turn {}: Agent {} {}; {} at ({}, {}) reopened".format(
                    event["turn"], event["agent_id"], event["reason"],
                    event["job"], x, y
                ))
        else:
            print("  None")

        print("\nDeaths:")
        if world_obj.death_events:
            for event in world_obj.death_events:
                print("  Turn {}: Agent {} died from {} at age {}".format(
                    event["turn"], event["agent_id"], event["cause"], event["age"]
                ))
        else:
            print("  None")

        print("\nAgent health:")
        for agent in self.all_agents:
            diseases = ", ".join(sorted(agent.diseases)) or "none"
            print("  Agent {}: {}/100; diseases: {}".format(agent.id, agent.health, diseases))

        print("\nAgent mental health:")
        for agent in self.all_agents:
            print("  Agent {}: {}/100".format(agent.id, agent.mental_health))

        print("\nAgent hunger:")
        for agent in self.all_agents:
            print("  Agent {}: {}/{}".format(
                agent.id, agent.hunger, agent.hunger_max
            ))

        print("\nAgent jobs:")
        for agent in self.all_agents:
            print("  Agent {}: {}".format(agent.id, agent.job or "unemployed"))

        print("\nCommunications:")
        if world_obj.communication_events:
            for event in world_obj.communication_events:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: Agent {} told Agent {} these building-free places: {}".format(
                    event["turn"], event["sender_id"], event["receiver_id"], locations
                ))
        else:
            print("  No messages were exchanged.")
        print("=" * 58)

    def print_batch_report(self, world_obj, start_turn, end_turn):
        """Print building and job events produced during one batch."""
        entries = [event for event in world_obj.building_entries
                   if start_turn <= event["turn"] <= end_turn]
        hires = [event for event in world_obj.hiring_events
                 if start_turn <= event["turn"] <= end_turn]
        rejections = [
            event for event in world_obj.job_application_events
            if not event["hired"]
            and start_turn <= event["turn"] <= end_turn
        ]
        quits = [event for event in world_obj.job_quit_events
                 if start_turn <= event["turn"] <= end_turn]
        school_events = [event for event in world_obj.school_events
                         if start_turn <= event["turn"] <= end_turn]
        disease_events = [event for event in world_obj.disease_events
                          if start_turn <= event["turn"] <= end_turn]
        communications = [
            event for event in world_obj.communication_events
            if start_turn <= event["turn"] <= end_turn
        ]
        print("\n" + "-" * 58)
        print("BATCH REPORT: Turns {}-{}".format(start_turn, end_turn))
        print("Building entries:")
        if entries:
            for event in entries:
                x, y = event["position"]
                print("  Turn {}: Agent {} entered type {} building at ({}, {})".format(
                    event["turn"], event["agent_id"], event["building_type"], x, y
                ))
        else:
            print("  None")

        print("Rejected job applications:")
        if rejections:
            for event in rejections:
                x, y = event["position"]
                print("  Turn {}: Agent {} was rejected from the {} at type {} building "
                      "({}, {}) (score: {}; required: {}).".format(
                    event["turn"], event["agent_id"], event["job"],
                    event["building_type"], x, y,
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("Disease events:")
        if disease_events:
            for event in disease_events:
                if event.get("source") == "natural":
                    print("  Turn {}: Agent {} contracted {} naturally".format(
                        event["turn"], event["agent_id"], event["disease"]
                    ))
                else:
                    print("  Turn {}: Agent {} caught {} passed by Agent {}".format(
                        event["turn"], event["agent_id"], event["disease"],
                        event["source_id"]
                    ))
        else:
            print("  None")

        print("School:")
        if school_events:
            for event in school_events:
                if event["event"] == "enrolled":
                    x, y = event["position"]
                    print("  Turn {}: Agent {} enrolled at ({}, {})".format(
                        event["turn"], event["agent_id"], x, y
                    ))
                else:
                    print("  Turn {}: Agent {} graduated; intelligence is now {}".format(
                        event["turn"], event["agent_id"], event["intelligence"]
                    ))
        else:
            print("  None")

        print("Jobs reopened:")
        if quits:
            for event in quits:
                x, y = event["position"]
                print("  Turn {}: Agent {} {}; {} at ({}, {}) reopened".format(
                    event["turn"], event["agent_id"], event["reason"],
                    event["job"], x, y
                ))
        else:
            print("  None")

        deaths = [event for event in world_obj.death_events
                  if start_turn <= event["turn"] <= end_turn]
        print("Deaths:")
        if deaths:
            for event in deaths:
                print("  Turn {}: Agent {} died from {} at age {}".format(
                    event["turn"], event["agent_id"], event["cause"], event["age"]
                ))
        else:
            print("  None")

        print("Agents hired:")
        if hires:
            for event in hires:
                print("  Turn {}: Agent {} got the {} (score: {}; required: {})".format(
                    event["turn"], event["agent_id"], event["job"],
                    event["score"], event["minimum_score"]
                ))
        else:
            print("  None")

        print("Communications:")
        if communications:
            for event in communications:
                locations = ", ".join(
                    "({}, {})".format(x, y)
                    for x, y in event["empty_locations"]
                ) or "none known"
                print("  Turn {}: Agent {} told Agent {} these building-free places: {}".format(
                    event["turn"], event["sender_id"], event["receiver_id"], locations
                ))
        else:
            print("  None")
        print("Open jobs: {}".format(world_obj.open_jobs))
        print("-" * 58)
