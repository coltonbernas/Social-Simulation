"""Simple region-to-region migration."""
import random


def setting(world_obj, key, fallback):
    return world_obj._setting("Migration", key, fallback)


def region_score(region):
    """Real wage: what the wage can buy after cost of living and housing prices."""
    return region["wage_multiplier"] / (
        region["cost_multiplier"] * region.get("housing_price_factor", 1.0))


def connections_who_moved(agent, by_id):
    """Friends (6+ points), parents and children who have already migrated."""
    ids = {other for other, points in agent.relationship_points.items() if points >= 6}
    ids |= agent.parent_ids | agent.children_ids
    return sum(1 for other in ids if other in by_id and by_id[other].has_migrated)


def move_agent(agent, world_obj, dest_id, cost):
    """Take the agent out of their old cell, drop job/house/school, place them in dest."""
    try:
        spot = agent.get_safe_spawn_pos(world_obj, world_obj.rows, world_obj.cols, dest_id)
    except RuntimeError:
        return False

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

    dest_name = world_obj.regions[dest_id]["name"]
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

    source_name = world_obj.regions[agent.region]["name"]
    agent.region = dest_id
    agent.pos_x, agent.pos_y = spot
    agent.previous_position = None
    agent.visited_positions.add(spot)
    world_obj.agent_grid[spot[0]][spot[1]] = agent.id
    agent.wealth -= cost
    agent.has_migrated = True
    print("Agent {} migrated from {} to {} (cost ${:,}).".format(
        agent.id, source_name, dest_name, cost))
    return True


def process_migration(population, world_obj):
    """Run once per turn: update housing prices, then let agents decide whether to move."""
    world_obj.update_housing_prices(population.agents)

    move_cost = setting(world_obj, "move_cost", 300)
    base_chance = setting(world_obj, "base_chance", 0.03)
    unemployed_bonus = setting(world_obj, "unemployed_bonus", 0.10)
    connection_bonus = setting(world_obj, "connection_bonus", 0.10)

    by_id = {agent.id: agent for agent in population.agents}
    for agent in list(population.agents):
        if agent.age < 18 or agent.diseases or agent.hospitalized_at is not None:
            continue
        if agent.wealth < move_cost:
            continue

        home = world_obj.regions[agent.region]
        others = [r for r in world_obj.regions if r["id"] != agent.region]
        best = max(others, key=region_score)
        if region_score(best) < region_score(home) * 1.1:
            continue   # not enough better to be worth moving

        chance = base_chance
        if agent.job is None:
            chance += unemployed_bonus
        chance += connection_bonus * min(3, connections_who_moved(agent, by_id))
        if random.random() < chance:
            move_agent(agent, world_obj, best["id"], move_cost)