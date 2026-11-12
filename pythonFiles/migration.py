"""Region-to-region migration with a wealth gap, entry barriers, refugees and tension."""
import random


def setting(world_obj, key, fallback):
    return world_obj._setting("Migration", key, fallback)


def region_score(region):
    """Real wage after tax, cost of living, housing prices, and social tension."""
    net_wage = region["wage_multiplier"] * (1 - region.get("tax_rate", 0.0))
    score = net_wage / (region["cost_multiplier"] * region.get("housing_price_factor", 1.0))
    return score * max(0.3, 1 - 0.5 * region.get("tension", 0.0))


def entry_cost(world_obj, dest):
    """Moving costs more in expensive regions and where many rich residents guard the gap."""
    base = setting(world_obj, "move_cost", 300)
    gatekeeping = setting(world_obj, "gatekeeping", 0.5)
    price_level = dest["cost_multiplier"] * dest.get("housing_price_factor", 1.0)
    barrier = 1 + gatekeeping * dest.get("rich_share", 0.0)
    return int(round(base * price_level * barrier))


def connections_who_moved(agent, by_id):
    """Friends (6+ points), parents and children who have already migrated."""
    ids = {other for other, points in agent.relationship_points.items() if points >= 6}
    ids |= agent.parent_ids | agent.children_ids
    return sum(1 for other in ids if other in by_id and by_id[other].has_migrated)


def move_agent(agent, world_obj, dest_id, cost, refugee=False):
    """Move an agent to another region; drop job/house/school. Refugees risk their health."""
    try:
        spot = agent.get_safe_spawn_pos(world_obj, world_obj.rows, world_obj.cols, dest_id)
    except RuntimeError:
        return False

    source_id = agent.region
    source_name = world_obj.regions[source_id]["name"]
    dest_name = world_obj.regions[dest_id]["name"]

    if refugee:
        agent.wealth -= cost
        if random.random() < setting(world_obj, "refugee_death_risk", 0.05):
            agent.damage_health(agent.health, "dangerous journey as a refugee", world_obj)
            print("Agent {} died trying to reach {} as a refugee.".format(agent.id, dest_name))
            return False
        agent.damage_health(setting(world_obj, "refugee_health_loss", 15),
                            "dangerous journey as a refugee", world_obj)

    old = (agent.pos_x, agent.pos_y)
    occupants = None
    for registry in (world_obj.school_occupants, world_obj.grocery_occupants,
                     world_obj.hospital_occupants, world_obj.houses):
        if old in registry:
            occupants = registry[old]
            break
    if occupants is not None:
        occupants.discard(agent.id)
    if world_obj.agent_grid[old[0]][old[1]] == agent.id:
        world_obj.agent_grid[old[0]][old[1]] = next(iter(occupants), 0) if occupants else 0

    if agent.job is not None:
        world_obj.reopen_job(agent.employed_at, agent, reason="moved to {}".format(dest_name))
        agent.job = None
        agent.employed_at = None
        agent.returning_to_job = False
    if agent.house is not None:
        world_obj.houses[agent.house].discard(agent.id)
        agent.house = None
        agent.house_turns_since_payment = 0
    if agent.schooling_at is not None:
        world_obj.school_occupants[agent.schooling_at].discard(agent.id)
        agent.schooling_at = None
        agent.school_turns = 0
    agent.applied_buildings.clear()

    agent.region = dest_id
    agent.pos_x, agent.pos_y = spot
    agent.previous_position = None
    agent.visited_positions.add(spot)
    world_obj.agent_grid[spot[0]][spot[1]] = agent.id
    if not refugee:
        agent.wealth -= cost
    agent.has_migrated = True

    world_obj.regions[dest_id]["immigrants"] += 1
    world_obj.regions[source_id]["emigrants"] += 1
    if refugee:
        dest = world_obj.regions[dest_id]
        dest["tension"] = min(1.0, dest["tension"]
                              + setting(world_obj, "tension_per_refugee", 0.15))
    turn = world_obj.turnNo + 1
    record = {"turn": turn, "agent_id": agent.id, "from": source_name, "to": dest_name,
              "cost": cost, "wealth_after": agent.wealth, "refugee": refugee}
    agent.migration_history.append(record)
    world_obj.migration_events.append(record)
    print("Agent {} {} from {} to {} (cost ${:,}).".format(
        agent.id, "fled as a refugee" if refugee else "migrated",
        source_name, dest_name, cost))
    return True


def process_migration(population, world_obj):
    """Once per turn: prices, stats, welfare, tension, then each agent decides to move."""
    world_obj.update_housing_prices(population.agents)
    world_obj.update_region_stats(population.agents, reprice=False)
    world_obj.distribute_welfare(population.agents)

    min_age = setting(world_obj, "min_age", 18)
    base_chance = setting(world_obj, "base_chance", 0.03)
    unemployed_bonus = setting(world_obj, "unemployed_bonus", 0.10)
    connection_bonus = setting(world_obj, "connection_bonus", 0.10)
    gap_threshold = setting(world_obj, "gap_threshold", 0.10)
    gap_bonus = setting(world_obj, "gap_bonus", 0.5)
    cushion = setting(world_obj, "savings_cushion", 2.0)
    rich_line = setting(world_obj, "rich_wealth_threshold", 3000)
    crowding_push = setting(world_obj, "crowding_push", 0.15)
    tension_push = setting(world_obj, "tension_push", 0.3)
    refugee_limit = setting(world_obj, "refugee_wealth_limit", 400)
    refugee_cost = setting(world_obj, "refugee_cost", 100)
    refugee_chance = setting(world_obj, "refugee_chance", 0.04)
    decay = setting(world_obj, "tension_decay", 0.9)
    tension_drain = setting(world_obj, "tension_mental_drain", 5)

    # Tension fades over time and hurts the mood of people living in tense regions.
    for region in world_obj.regions:
        region["tension"] *= decay
    for agent in population.agents:
        tension = world_obj.regions[agent.region]["tension"]
        if tension > 0.01:
            agent.mental_health = max(
                0, agent.mental_health - tension_drain * tension * (1 - agent.resilience))

    by_id = {agent.id: agent for agent in population.agents}
    for agent in list(population.agents):
        if agent.age < min_age or agent.diseases or agent.hospitalized_at is not None:
            continue

        home = world_obj.regions[agent.region]
        home_score = region_score(home)
        others = [r for r in world_obj.regions if r["id"] != agent.region]
        moved = False

        # Normal move: must afford the entry cost (with savings) and a job must be open there.
        options = []
        for dest in others:
            cost = entry_cost(world_obj, dest)
            if agent.wealth < cost * cushion or dest["open_jobs"] <= 0:
                continue
            options.append((dest, cost))
        if options:
            dest, cost = max(options, key=lambda option: region_score(option[0]))
            gap = region_score(dest) / home_score - 1
            push = 0.0
            if agent.wealth >= rich_line:   # the rich leave crowded, tense regions
                push = (crowding_push * max(0.0, home["housing_price_factor"] - 1)
                        + tension_push * home["tension"])
            if gap >= gap_threshold or push > 0.02:
                chance = base_chance + gap_bonus * max(0.0, gap) + push
                if agent.job is None:
                    chance += unemployed_bonus
                chance += connection_bonus * min(3, connections_who_moved(agent, by_id))
                if random.random() < chance:
                    moved = move_agent(agent, world_obj, dest["id"], cost)
        if moved:
            continue

        # Refugee move: poor and jobless, cheap but risky, heads for the best region.
        if agent.job is None and refugee_cost <= agent.wealth < refugee_limit:
            dest = max(others, key=region_score)
            gap = region_score(dest) / home_score - 1
            if gap >= gap_threshold and random.random() < refugee_chance * (1 + gap):
                move_agent(agent, world_obj, dest["id"], refugee_cost, refugee=True)