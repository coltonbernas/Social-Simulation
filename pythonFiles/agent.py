import random

try:
    from .config import (
        grid_rows, grid_cols, health_min, health_max, starting_health_min,
        hunger_drain_per_step, hunger_damage_per_step, starting_wealth,
        low_wealth_threshold, low_wealth_stress_turns,
        grocery_hunger_threshold, grocery_food_cost,
        grocery_food_health_restore, grocery_food_mental_restore,
        mental_health_recovery_per_turn,
        stress_mental_health_initial_drain, stress_mental_health_sustained_drain,
        building_names,
    )
except ImportError:
    from config import (
        grid_rows, grid_cols, health_min, health_max, starting_health_min,
        hunger_drain_per_step, hunger_damage_per_step, starting_wealth,
        low_wealth_threshold, low_wealth_stress_turns,
        grocery_hunger_threshold, grocery_food_cost,
        grocery_food_health_restore, grocery_food_mental_restore,
        mental_health_recovery_per_turn,
        stress_mental_health_initial_drain, stress_mental_health_sustained_drain,
        building_names,
    )

try:
    from .disease import (
        disease_hunger_cost, random_immune_system, disease_name,
        validate_immune_system,
    )
except ImportError:
    from disease import (
        disease_hunger_cost, random_immune_system, disease_name,
        validate_immune_system,
    )


def random_intelligence():
    """Sample an IQ-style score using the percentages in the supplied chart."""
    score_range = random.choices(
        population=[(40, 69), (70, 79), (80, 89), (90, 109), (110, 119), (120, 129), (130, 145)],
        weights=[2.2, 6.7, 16.1, 50.0, 16.1, 6.7, 2.2],
        k=1,
    )[0]
    return random.randint(*score_range)


ETHNICITY_TYPES = (
    "East & Southeast Asian",
    "South Asian",
    "Arab & Middle Eastern",
    "African (Sub-Saharan)",
    "European & Slavic",
    "Indigenous Peoples of the Americas",
    "Indigenous Peoples of Oceania",
    "Latino / Mestizo Populations",
)

RELIGION_DISTRIBUTIONS = {
    "East & Southeast Asian": {
        "Unaffiliated": 52, "Buddhism": 17, "Folk / Traditional Religions": 17,
        "Islam": 13, "Christianity": 8,
    },
    "South Asian": {
        "Hinduism": 65, "Islam": 31, "Sikhism": 1.75,
        "Buddhism": 1.5, "Christianity": 1.75,
    },
    "Arab & Middle Eastern": {
        "Islam": 92.5, "Christianity": 4.5, "Judaism": 1.75,
        "Other / Unaffiliated / Druze / Baha'i": 1.25,
    },
    "African (Sub-Saharan)": {
        "Christianity": 62.5, "Islam": 31,
        "Traditional African Religions / Animism": 4, "Unaffiliated": 2.5,
    },
    "European & Slavic": {
        "Christianity": 73.5, "Unaffiliated": 21.5, "Islam": 5.5,
        "Other / Judaism / Buddhism": 1.5,
    },
    "Indigenous Peoples of the Americas": {
        "Christianity": 82.5, "Traditional Indigenous / Syncretic Beliefs": 12.5,
        "Unaffiliated": 6,
    },
    "Indigenous Peoples of Oceania": {
        "Christianity": 82.5, "Traditional / Customary Beliefs": 10,
        "Unaffiliated": 7.5,
    },
    "Latino / Mestizo Populations": {
        "Roman Catholicism": 67.5,
        "Protestant / Evangelical / Pentecostal": 20,
        "Unaffiliated / Secular": 9,
        "Other / Spiritist / Afro-Latin Traditions": 3.5,
    },
}


def random_religion(ethnicity_percentages):
    """Choose a religion using the ethnicity weighted regional percentages."""
    weights = {}
    for ethnicity, ethnicity_percentage in ethnicity_percentages.items():
        distribution = RELIGION_DISTRIBUTIONS.get(ethnicity)
        if distribution is None:
            continue
        for religion, percentage in distribution.items():
            weights[religion] = weights.get(religion, 0) + (
                ethnicity_percentage * percentage
            )

    if not weights:
        return "Unaffiliated"
    return random.choices(
        population=list(weights), weights=list(weights.values()), k=1
    )[0]


class Agent:
    def __init__(self, agent_id, world_obj, rows=None, cols=None, age=None,
                 ethnicity=None, ethnicity_percentages=None, parent_ids=None,
                 birth_turn=None, religion=None, region_id=None,
                 original_immune_system=None):
        # Dynamically fetch world dimensions from world_obj if not explicitly supplied
        if rows is None:
            rows = getattr(world_obj, "rows", grid_rows)
        if cols is None:
            cols = getattr(world_obj, "cols", grid_cols)

        # Retrieve dynamic health and wealth values from world_obj.config if available
        config = getattr(world_obj, "config", {})
        agent_cfg = config.get("Agent & Population", config) if isinstance(config, dict) else {}

        cfg_h_min = agent_cfg.get("health_min", health_min)
        cfg_h_max = agent_cfg.get("health_max", health_max)
        cfg_start_h_min = agent_cfg.get("starting_health_min", starting_health_min)
        cfg_start_wealth = agent_cfg.get("starting_wealth", starting_wealth)

        self.id = agent_id + 1
        self.name = "Agent {}".format(self.id)
        self.gender = random.choice(("female", "male"))
        self.age = random.randint(1, 30) if age is None else age
        self.death_age = random.randint(80, 100)
        self.intelligence = random_intelligence()

        # Calculate spawn health using dynamic config parameters
        spawn_health_min = max(cfg_h_min, min(cfg_start_h_min, cfg_h_max))
        self.health = random.randint(spawn_health_min, cfg_h_max)
        self.last_health_damage_cause = None
        self.diseases = set()
        self.pending_diseases = set()
        self.disease_info = {} # Maps disease_id -> {"turns_active": 0, "is_vaccinated": False}
        self.distrust = random.uniform(0, 1)
        self.vaccination_expiry = {} # disease_id -> turn_number
        self.original_immune_system = (
            original_immune_system
            if original_immune_system is not None
            else random_immune_system()
        )
        validate_immune_system(self.original_immune_system)
        self.immune_system = self.original_immune_system
        self.disease_info = {} 

        self.willpower = random.randint(0, 100)
        self.mental_health = 100
        self.wealth = cfg_start_wealth
        self.house = None
        self.house_turns_since_payment = 0
        self.house_rent_days = 0.0
        self.low_wealth_turns = 0
        self.job = None
        self.employed_at = None
        self.returning_to_job = False
        self.hospitalized_at = None
        self.hospital_stay_turns = 0
        self.hospital_visit_event = None
        self.applied_buildings = {}
        self.hunger_max = 100
        self.hunger = self.hunger_max
        self.active_stressful_events = set()
        self.political_status = None # to do
        self.birth_place = None
        self.birth_date = None
        self.ethnicity = ethnicity or random.choice(ETHNICITY_TYPES)
        self.ethnicity_percentages = (
            dict(ethnicity_percentages) if ethnicity_percentages is not None
            else {self.ethnicity: 100.0}
        )
        self.religion = (
            religion if religion is not None
            else random_religion(self.ethnicity_percentages)
        )
        self.parent_ids = set(parent_ids or ())
        self.children_ids = set()
        self.birth_turn = birth_turn
        self.has_migrated = False
        self.migration_history = []   # one dict per move: turn, from/to region, cost, wealth_after
        self.migration_target_region = None
        self.migration_target_position = None
        self.migration_source_region = None
        self.personality_type = random.choice((
            "introverted", "extroverted", "ambivert"
        ))
        self.inheritance = None
        self.genes = []
        self.education = None
        self.school_completed = False
        self.schooling_at = None
        self.school_turns = 0
        self.marital_status = None # somewhat done
        self.morality = None
        self.empathy = random.random()
        self.resilience = random.random()
        self.agreeableness = None
        self.openness = random.random()
        self.implusiveness = None
        self.creativity = None
        self.needs = {}
        self.confidence = None

        # Safe spawn evaluation across full active grid space
        self.pos_x, self.pos_y = self.get_safe_spawn_pos(world_obj, rows, cols, region_id)
        # birth_region never changes; region is where the agent lives now.
        self.birth_region = world_obj.region_of(self.pos_x, self.pos_y)
        self.birth_place = world_obj.regions[self.birth_region]["name"]
        self.region = self.birth_region

        self.known_empty = set()
        self.visited_positions = {(self.pos_x, self.pos_y)}
        self.position_visits = {(self.pos_x, self.pos_y): 1}
        self.previous_position = None
        self.interacted_agents = []
        self.interaction_last_turn = {}
        self.visible_agent_ids = set()
        self.relationship_points = {}
        self.dating_partner_id = None
        self.dating_since_turn = None


        world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        print("Agent {} spawned at ({},{}); age: {}; natural death age: {}; "
              "intelligence: {}; willpower: {}; personality: {}; gender: {}; "
              "ethnicity: {}; religion: {}".format(
            self.id, self.pos_x, self.pos_y, self.age, self.death_age,
            self.intelligence, self.willpower, self.personality_type, self.gender,
            self.ethnicity, self.religion
        ))

    def get_safe_spawn_pos(self, world_obj, rows, cols, region_id=None):
        if region_id is None:
            x_min, x_max, y_min, y_max = 0, rows - 1, 0, cols - 1
        else:
            region = world_obj.regions[region_id]
            x_min, x_max = region["row_start"], region["row_end"]
            y_min, y_max = region["col_start"], region["col_end"]

        for _ in range(1000):
            x = random.randint(x_min, x_max)
            y = random.randint(y_min, y_max)
            if self.is_position_safe(x, y, world_obj, rows, cols):
                return x, y
        raise RuntimeError("Could not find a valid spawn position")

    def in_my_region(self, world_obj, location):
        return world_obj.region_of(location[0], location[1]) == self.region

    def is_position_safe(self, x, y, world_obj, rows, cols):
        # Ensure starting position (x, y) itself is inside bounds
        if not (0 <= x < rows and 0 <= y < cols):
            return False

        # Check neighbor positions safely
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]:
            nx, ny = x + dx, y + dy
            # Only inspect cells that are strictly inside grid boundaries
            if 0 <= nx < rows and 0 <= ny < cols:
                if world_obj.grid[nx][ny] != 0:
                    return False
        return True

    def scan_surroundings(self, world_obj, rows, cols):
        visible_buildings = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = self.pos_x + dx, self.pos_y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] != 0:
                        visible_buildings.append((nx, ny))
        return visible_buildings

    def scan_empty_surroundings(self, world_obj, rows, cols):
        """Return nearby cells that do not contain buildings."""
        empty_locations = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = self.pos_x + dx, self.pos_y + dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if world_obj.grid[nx][ny] == 0:
                        empty_locations.append((nx, ny))
        return empty_locations

    def receive_message(self, empty_locations):
        """Remember cells another agent reports as building-free."""
        self.known_empty.update(empty_locations)

    def _get_cfg_val(self, world_obj, category, key, fallback):
        """Helper to read active dynamic parameters from world_obj.config."""
        if not world_obj or not hasattr(world_obj, "config") or not world_obj.config:
            return fallback
        cfg = world_obj.config
        # Check nested dictionary path first, then flat dictionary path
        if category in cfg and isinstance(cfg[category], dict):
            return cfg[category].get(key, fallback)
        return cfg.get(key, fallback)

    def damage_health(self, amount, cause, world_obj=None):
        """Reduce health and remember what caused the latest reduction."""
        h_min = self._get_cfg_val(world_obj, "Agent & Population", "health_min", health_min)
        previous_health = self.health
        self.health = max(h_min, self.health - amount)
        if self.health < previous_health:
            self.last_health_damage_cause = cause

    def update_health(self, world_obj=None):
        """Apply hunger, starvation, health recovery, and stressful-event effects."""
        hunger_drain = self._get_cfg_val(world_obj, "Grocery & Needs", "hunger_drain_per_step", hunger_drain_per_step)
        self.hunger = max(
            0, self.hunger - hunger_drain - disease_hunger_cost(self)
        )

        h_max = self._get_cfg_val(world_obj, "Agent & Population", "health_max", health_max)
        previous_health = self.health
        self.health = min(h_max, self.health + 1)
        if self.health > previous_health:
            self.last_health_damage_cause = None

        if self.hunger <= 0:
            damage = self._get_cfg_val(world_obj, "Grocery & Needs", "hunger_damage_per_step", hunger_damage_per_step)
            self.damage_health(damage, "hunger", world_obj)

        self.update_stressful_events(world_obj)

    def earn_income(self, world_obj):
        """Add this turn's wages after the home region's income tax."""
        gross = world_obj.income_for(self.job, self.region)
        tax = world_obj.collect_tax(self.region, gross)
        self.wealth += gross - tax

    def advance_school(self, world_obj):
        """Count attendance turns and award intelligence after five turns."""
        if self.schooling_at is None or (self.pos_x, self.pos_y) != self.schooling_at:
            return
        self.school_turns += 1
        if self.school_turns >= 5:
            self.intelligence += 20
            self.school_completed = True
            self.schooling_at = None
            self.applied_buildings.clear()
            world_obj.school_events.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "event": "graduated",
                "intelligence": self.intelligence,
            })
            print("Agent {} completed school; intelligence increased by 20 to {}.".format(
                self.id, self.intelligence
            ))

    def can_seek_school(self, world_obj):
        if self.job is not None or self.school_completed or self.schooling_at is not None:
            return False
        available_jobs = [
            location for location, holders in world_obj.building_jobs.items()
            if len(holders) < world_obj.job_capacities[location]
               and self.can_apply_for_type(world_obj.grid[location[0]][location[1]], world_obj)
               and self.applied_buildings.get(location)
               != world_obj.job_opening_versions[location]
               and self.in_my_region(world_obj, location)
        ]
        school_nearby = any(
            max(abs(location[0] - self.pos_x), abs(location[1] - self.pos_y)) <= 1
            for location in world_obj.school_occupants
        )
        return school_nearby or not available_jobs

    def update_stressful_events(self, world_obj=None):
        """Apply immediate and sustained mental-health costs from stressors."""
        wealth_line = self._get_cfg_val(
            world_obj, "Economy & Jobs", "low_wealth_threshold", low_wealth_threshold)
        stress_turns = self._get_cfg_val(
            world_obj, "Economy & Jobs", "low_wealth_stress_turns", low_wealth_stress_turns)
        initial_drain = self._get_cfg_val(
            world_obj, "Mental Health & Stress", "stress_mental_health_initial_drain",
            stress_mental_health_initial_drain)
        sustained_drain = self._get_cfg_val(
            world_obj, "Mental Health & Stress", "stress_mental_health_sustained_drain",
            stress_mental_health_sustained_drain)
        recovery = self._get_cfg_val(
            world_obj, "Mental Health & Stress", "mental_health_recovery_per_turn",
            mental_health_recovery_per_turn)

        current_events = set()
        if self.wealth < wealth_line:
            self.low_wealth_turns += 1
            if self.low_wealth_turns > stress_turns:
                current_events.add("low_wealth")
        else:
            self.low_wealth_turns = 0
        if self.hunger <= 0:
            current_events.add("hunger")

        for event in current_events:
            if event not in self.active_stressful_events:
                # A new stressful event has an immediate impact.
                self.mental_health = max(
                    0, self.mental_health
                    - initial_drain * (1 - self.resilience)
                )
            else:
                # The impact continues on every turn the event remains active.
                self.mental_health = max(
                    0, self.mental_health
                    - sustained_drain * (1 - self.resilience)
                )
        if not current_events:
            self.mental_health = min(100, self.mental_health + recovery)
        self.active_stressful_events = current_events

    def can_buy_food(self, world_obj):
        cost = world_obj.food_cost(self.region, self)
        threshold = self._get_cfg_val(world_obj, "Grocery & Needs",
                                      "grocery_hunger_threshold", grocery_hunger_threshold)
        return self.wealth >= cost and self.hunger < threshold

    def buy_house(self, world_obj, location):
        """Rent an available home by paying its first four days upfront."""
        house_type = world_obj.grid[location[0]][location[1]]
        if self.house is not None or house_type not in (6, 7, 11, 12):
            return False
        if not self.in_my_region(world_obj, location):
            return False
        if not world_obj.can_accept_resident(location, self):
            return False
        cost = world_obj.house_cost(house_type, self.region)
        if self.wealth < cost:
            return False
        self.wealth -= cost
        self.house = location
        world_obj.house_owners.setdefault(location, self.id)
        self.house_turns_since_payment = 0
        self.house_rent_days = 0.0
        world_obj.houses[location].add(self.id)
        event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                 "event": "bought", "house_type": house_type,
                 "position": location, "amount": cost, "wealth": self.wealth}
        world_obj.house_events.append(event)
        print("Agent {} bought a {} for ${:,} (wealth: ${:,}).".format(
            self.id, building_names[house_type], cost, self.wealth
        ))
        return True

    def advance_house_stay(self, world_obj):
        """Restore mood and collect rent for each four calendar days lived."""
        if self.house is None:
            return
        house_type = world_obj.grid[self.house[0]][self.house[1]]
        if (self.pos_x, self.pos_y) == self.house:
            quality = world_obj.regions[world_obj.region_of(*self.house)]["home_quality"]
            housing_recovery = {6: 5, 7: 15, 11: 2, 12: 0}.get(house_type, 0) * quality
            self.mental_health = min(100, self.mental_health + housing_recovery)
        self.house_rent_days += getattr(world_obj, "time_step_days", 1.0)
        rent_periods = int(self.house_rent_days // 4)
        if rent_periods < 1:
            return
        period_cost = world_obj.house_cost(house_type, world_obj.region_of(*self.house))
        cost = period_cost * rent_periods
        if self.wealth >= cost:
            self.wealth -= cost
            self.house_rent_days -= rent_periods * 4
            self.house_turns_since_payment = int(self.house_rent_days)
            event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                     "event": "paid", "house_type": house_type,
                     "position": self.house, "amount": cost, "wealth": self.wealth}
            world_obj.house_events.append(event)
            print("Agent {} paid ${:,} rent for the {} (wealth: ${:,}).".format(
                self.id, cost, building_names[house_type], self.wealth
            ))
        else:
            location = self.house
            world_obj.houses[location].discard(self.id)
            self.house = None
            self.house_turns_since_payment = 0
            self.house_rent_days = 0.0
            self.mental_health = max(
                0, self.mental_health - 25 * (1 - self.resilience)
            )
            event = {"turn": world_obj.turnNo + 1, "agent_id": self.id,
                     "event": "evicted", "house_type": house_type,
                     "position": location, "amount": cost, "wealth": self.wealth,
                     "mental_health": self.mental_health}
            world_obj.house_events.append(event)
            print("Agent {} was evicted from the {}; lost 25 mental health (now {}).".format(
                self.id, building_names[house_type], self.mental_health
            ))

    def buy_food(self, world_obj, location):
        """Buy food at a grocery store and restore hunger, health, and mood."""
        if location not in world_obj.grocery_stores or not self.can_buy_food(world_obj):
            return False

        cost = world_obj.food_cost(self.region, self)
        h_max = self._get_cfg_val(world_obj, "Agent & Population", "health_max", health_max)
        health_restore = self._get_cfg_val(world_obj, "Grocery & Needs",
                                           "grocery_food_health_restore", grocery_food_health_restore)
        mental_restore = self._get_cfg_val(world_obj, "Grocery & Needs",
                                           "grocery_food_mental_restore", grocery_food_mental_restore)

        self.wealth -= cost
        self.hunger = self.hunger_max
        self.health = min(h_max, self.health + health_restore)
        self.mental_health = min(100, self.mental_health + mental_restore)
        event = {
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "position": location,
            "cost": cost,
            "wealth": self.wealth,
            "health": self.health,
            "mental_health": self.mental_health,
            "hunger": self.hunger,
        }
        world_obj.grocery_events.append(event)
        if self.job == "Type 2 job":
            self.returning_to_job = True
        print("Agent {} bought food for ${:,} at the grocery store; hunger {}, health {}, mental health {}, wealth ${:,}.".format(
            self.id, cost, self.hunger, self.health, self.mental_health, self.wealth
        ))
        return True

    def advance_hospital_stay(self, world_obj):
        """Keep an agent hospitalized until immune repair clears every infection."""
        if self.hospitalized_at is None:
            return False
        self.hospital_stay_turns += 1
        if self.diseases or self.pending_diseases:
            return False

        cured_diseases = (
            self.hospital_visit_event["diseases"]
            if self.hospital_visit_event is not None
            else ()
        )
        if self.hospital_visit_event is not None:
            self.hospital_visit_event["cured_turn"] = world_obj.turnNo + 1
            self.hospital_visit_event["turns_in_hospital"] = self.hospital_stay_turns
            self.hospital_visit_event["outcome"] = "cured"
            self.hospital_visit_event = None
        self.hospitalized_at = None
        self.hospital_stay_turns = 0
        occupants = world_obj.workplace_occupants.get((self.pos_x, self.pos_y))
        if occupants is None:
            occupants = world_obj.hospital_occupants.get((self.pos_x, self.pos_y))
        if occupants is not None:
            occupants.discard(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == self.id:
                world_obj.agent_grid[self.pos_x][self.pos_y] = next(iter(occupants), 0)
        print("Agent {} completed hospital treatment and recovered from {}.".format(
            self.id, ", ".join(disease_name(disease) for disease in cured_diseases) or "illness"
        ))
        return True

    def move(self, world_obj, rows=None, cols=None):
        """Move the agent toward active goals while dynamically respecting current world dimensions."""
        # Dynamically pull grid dimensions from world_obj if not explicitly passed
        if rows is None:
            rows = getattr(world_obj, "rows", grid_rows)
        if cols is None:
            cols = getattr(world_obj, "cols", grid_cols)

        # Migration advances one neighboring tile at a time in process_migration.
        if self.migration_target_region is not None:
            return None

        if self.hospitalized_at is not None:
            print("Agent {} is staying in the hospital for treatment.".format(self.id))
            return None
        higher_job_available = self.has_higher_paying_job(world_obj)
        if (self.job == "Type 2 job" and not self.can_buy_food(world_obj)
                and not self.diseases
                and not self.returning_to_job
                and not higher_job_available):
            print("Agent {} is staying at their type 2 job.".format(self.id))
            return None
        if (self.job == "Type 2 job" and self.returning_to_job
                and not self.diseases
                and (self.pos_x, self.pos_y) == self.employed_at):
            self.returning_to_job = False
            print("Agent {} returned to their type 2 job and is staying there.".format(self.id))
            return None
        if self.schooling_at is not None and not self.diseases:
            print("Agent {} is attending school ({}/5 turns).".format(
                self.id, self.school_turns
            ))
            return None

        # A resident stays home unless a health or food need sends them out.
        if (self.house is not None and (self.pos_x, self.pos_y) == self.house
                and not self.diseases and not self.can_buy_food(world_obj)
                and not higher_job_available):
            return None

        visible_buildings = self.scan_surroundings(world_obj, rows, cols)
        job_targets = [
            location for location, job_holders in world_obj.building_jobs.items()
            if self.can_apply_for_type(world_obj.grid[location[0]][location[1]], world_obj)
               and self.applied_buildings.get(location)
               != world_obj.job_opening_versions[location]
               and len(job_holders) < world_obj.job_capacities[location]
               and self.in_my_region(world_obj, location)
        ]
        visible_empty = self.scan_empty_surroundings(world_obj, rows, cols)
        self.known_empty.update(visible_empty)
        self.known_empty.difference_update(visible_buildings)

        school_target = None
        if self.can_seek_school(world_obj):
            school_target = min(
                world_obj.school_occupants,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )

        grocery_target = None
        if self.can_buy_food(world_obj):
            grocery_target = min(
                world_obj.grocery_stores,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )
            if (grocery_target == (self.pos_x, self.pos_y)
                    and not self.diseases):
                self.buy_food(world_obj, grocery_target)
                return None

        hospital_target = None
        if self.diseases:
            hospital_target = min(
                world_obj.hospitals,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
                default=None,
            )

        house_target = None
        if self.house is not None:
            house_target = self.house
        elif not self.diseases:
            affordable_houses = [
                location for location in world_obj.houses
                if self.in_my_region(world_obj, location)
                   and world_obj.can_accept_resident(location, self)
                   and self.wealth >= world_obj.house_cost(
                    world_obj.grid[location[0]][location[1]], self.region)
            ]
            house_target = min(
                affordable_houses,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y), location
                ), default=None,
            )

        if hospital_target is not None:
            target_x, target_y = hospital_target
        elif grocery_target is not None:
            target_x, target_y = grocery_target
        elif self.job == "Type 2 job" and self.returning_to_job:
            target_x, target_y = self.employed_at
        elif school_target is not None:
            target_x, target_y = school_target
        elif job_targets:
            target_x, target_y = min(
                job_targets,
                key=lambda location: (
                    abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                    location,
                ),
            )
        elif house_target is not None:
            target_x, target_y = house_target
        else:
            target_x = target_y = None

        # A previously rejected agent may already be standing in a building
        # when its job reopens, so it can apply again without walking out and back in.
        if school_target == (self.pos_x, self.pos_y):
            self.start_school(world_obj, school_target)
            return None

        if (target_x, target_y) == (self.pos_x, self.pos_y):
            if (self.house is None
                    and world_obj.grid[self.pos_x][self.pos_y] in (6, 7, 11, 12)):
                self.buy_house(world_obj, (self.pos_x, self.pos_y))
                if self.house is not None:
                    return None
            self.apply_for_job(
                world_obj,
                world_obj.grid[self.pos_x][self.pos_y],
                (self.pos_x, self.pos_y),
            )
            job_targets = [
                location for location, job_holders in world_obj.building_jobs.items()
                if self.can_apply_for_type(world_obj.grid[location[0]][location[1]], world_obj)
                   and self.applied_buildings.get(location)
                   != world_obj.job_opening_versions[location]
                   and len(job_holders) < world_obj.job_capacities[location]
                   and self.in_my_region(world_obj, location)
            ]
            if self.job == "Type 2 job":
                return None
            if job_targets:
                target_x, target_y = min(
                    job_targets,
                    key=lambda location: (
                        abs(location[0] - self.pos_x) + abs(location[1] - self.pos_y),
                        location,
                    ),
                )
            else:
                target_x = target_y = None

        preferred_moves = []
        if target_x is not None:
            step_x = 1 if target_x > self.pos_x else (-1 if target_x < self.pos_x else 0)
            step_y = 1 if target_y > self.pos_y else (-1 if target_y < self.pos_y else 0)

            if step_x != 0 and step_y != 0:
                preferred_moves = [(step_x, 0), (0, step_y)]
            else:
                preferred_moves = [(step_x, step_y)]
            if (target_x, target_y) in visible_buildings:
                print("Agent {} spotted a {} at ({}, {}).".format(
                    self.id, building_names[world_obj.grid[target_x][target_y]], target_x, target_y
                ))

        possible_moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        unexplored_moves = []
        new_position_moves = []
        legal_preferred_moves = []
        fallback_moves = []
        blocked_moves = []
        move_destinations = {}
        for move_x, move_y in possible_moves:
            next_x = max(0, min(rows - 1, self.pos_x + move_x))
            next_y = max(0, min(cols - 1, self.pos_y + move_y))
            move = (move_x, move_y)
            destination = (next_x, next_y)
            if destination == (self.pos_x, self.pos_y):
                continue
            if (world_obj.agent_grid[next_x][next_y] not in (0, self.id)
                    and world_obj.grid[next_x][next_y] not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)):
                blocked_moves.append(move)
                continue
            fallback_moves.append(move)
            move_destinations[move] = destination
            if destination not in self.known_empty:
                unexplored_moves.append(move)
            if destination not in self.visited_positions:
                new_position_moves.append(move)
            if move in preferred_moves:
                legal_preferred_moves.append(move)

        # Explore locations with unknown building status first, then locations
        # this agent has not physically visited. Revisit old locations only
        # when needed, preferring the least-visited route.
        if legal_preferred_moves:
            dx, dy = random.choice(legal_preferred_moves)
        elif target_x is not None and fallback_moves:
            current_distance = abs(target_x - self.pos_x) + abs(target_y - self.pos_y)
            progress_moves = [
                move for move in fallback_moves
                if abs(move_destinations[move][0] - target_x)
                   + abs(move_destinations[move][1] - target_y) < current_distance
            ]
            if progress_moves:
                best_distance = min(
                    abs(move_destinations[move][0] - target_x)
                    + abs(move_destinations[move][1] - target_y)
                    for move in progress_moves
                )
                best_moves = [
                    move for move in progress_moves
                    if abs(move_destinations[move][0] - target_x)
                       + abs(move_destinations[move][1] - target_y) == best_distance
                ]
                dx, dy = random.choice(best_moves)
            elif unexplored_moves:
                dx, dy = random.choice(unexplored_moves)
            elif new_position_moves:
                dx, dy = random.choice(new_position_moves)
            else:
                dx, dy = random.choice(fallback_moves)
        elif unexplored_moves:
            dx, dy = random.choice(unexplored_moves)
        elif new_position_moves:
            dx, dy = random.choice(new_position_moves)
        elif fallback_moves:
            alternatives = [
                move for move in fallback_moves
                if move_destinations[move] != self.previous_position
            ]
            if not alternatives:
                alternatives = fallback_moves
            least_visited_count = min(
                self.position_visits.get(move_destinations[move], 0)
                for move in alternatives
            )
            least_visited_moves = [
                move for move in alternatives
                if self.position_visits.get(move_destinations[move], 0) == least_visited_count
            ]
            dx, dy = random.choice(least_visited_moves)
        elif blocked_moves:
            # Only attempt a blocked move if every available direction is occupied.
            dx, dy = random.choice(blocked_moves)
        else:
            dx = dy = 0

        next_x = max(0, min(rows - 1, self.pos_x + dx))
        next_y = max(0, min(cols - 1, self.pos_y + dy))
        other_agent_id = world_obj.agent_grid[next_x][next_y]
        if (other_agent_id not in (0, self.id)
                and world_obj.grid[next_x][next_y] not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)):
            print("Agent {} bumped into Agent {} at ({}, {}).".format(
                self.id, other_agent_id, next_x, next_y
            ))
            return other_agent_id

        old_position = (self.pos_x, self.pos_y)
        old_shared_occupants = world_obj.workplace_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.school_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.grocery_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.hospital_occupants.get(old_position)
        if old_shared_occupants is None:
            old_shared_occupants = world_obj.houses.get(old_position)
        if old_shared_occupants is not None:
            old_shared_occupants.discard(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == self.id:
                world_obj.agent_grid[self.pos_x][self.pos_y] = (
                    next(iter(old_shared_occupants)) if old_shared_occupants else 0
                )
        else:
            world_obj.agent_grid[self.pos_x][self.pos_y] = 0
        self.pos_x, self.pos_y = next_x, next_y
        if self.diseases and self.schooling_at is not None:
            self.schooling_at = None
            self.school_turns = 0
        if (self.job == "Type 2 job" and self.returning_to_job
                and (self.pos_x, self.pos_y) == self.employed_at):
            self.returning_to_job = False
        self.previous_position = old_position
        new_position = (self.pos_x, self.pos_y)
        self.visited_positions.add(new_position)
        self.position_visits[new_position] = self.position_visits.get(new_position, 0) + 1

        building_location = (self.pos_x, self.pos_y)
        if world_obj.grid[self.pos_x][self.pos_y] in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            occupants = world_obj.workplace_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.school_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.grocery_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.hospital_occupants.get(building_location)
            if occupants is None:
                occupants = world_obj.houses.get(building_location)
            occupants.add(self.id)
            if world_obj.agent_grid[self.pos_x][self.pos_y] == 0:
                world_obj.agent_grid[self.pos_x][self.pos_y] = self.id
        else:
            world_obj.agent_grid[self.pos_x][self.pos_y] = self.id

        print("Agent {} moved to ({}, {})".format(self.id, self.pos_x, self.pos_y))

        building_type = world_obj.grid[self.pos_x][self.pos_y]
        if building_type and old_position != building_location:
            world_obj.building_entries.append({
                "turn": world_obj.turnNo + 1,
                "agent_id": self.id,
                "building_type": building_type,
                "position": building_location,
            })
            print("Agent {} entered the {} at ({}, {}).".format(
                self.id, building_names[building_type], self.pos_x, self.pos_y
            ))
            if building_type in world_obj.building_jobs:
                self.apply_for_job(world_obj, building_type, building_location)
            elif building_type == 3 and school_target == building_location:
                self.start_school(world_obj, building_location)
            elif building_type == 4:
                self.buy_food(world_obj, building_location)
            elif building_type == 5:
                if self.diseases:
                    self.hospitalized_at = building_location
                    self.hospital_stay_turns = 0
                    self.hospital_visit_event = {
                        "admitted_turn": world_obj.turnNo + 1,
                        "agent_id": self.id,
                        "position": building_location,
                        "diseases": sorted(self.diseases),
                        "cured_turn": None,
                        "turns_in_hospital": None,
                        "outcome": "in treatment",
                    }
                    world_obj.hospital_events.append(self.hospital_visit_event)
                    if self.job == "Type 2 job":
                        self.returning_to_job = True
                    print("Agent {} entered the hospital with {}; immune repair is accelerated.".format(
                        self.id, ", ".join(
                            disease_name(disease) for disease in sorted(self.diseases)
                        )
                    ))
                self.try_vaccinate(world_obj)
            elif building_type in (6, 7, 11, 12):
                if self.house == building_location:
                    return None
                self.buy_house(world_obj, building_location)

    def start_school(self, world_obj, location):
        """Enroll the agent at a school; multiple agents may share its tile."""
        if self.job is not None or self.school_completed or self.schooling_at is not None:
            return False
        self.schooling_at = location
        self.school_turns = 0
        world_obj.school_occupants[location].add(self.id)
        world_obj.school_events.append({
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "event": "enrolled",
            "position": location,
        })
        print("Agent {} enrolled in school at ({}, {}).".format(
            self.id, location[0], location[1]
        ))
        return True

    def try_vaccinate(self, world_obj):
        """Offer all available vaccines to the agent, respecting distrust."""
        if not world_obj.available_vaccines:
            return
        
        # High distrust means they reject ALL vaccines
        if self.distrust > 0.5:
            return

        from disease import disease_name
        for d_id in world_obj.available_vaccines:
            # Don't vaccinate if already immune or recently vaccinated
            if d_id in self.diseases or d_id in self.pending_diseases:
                continue
            
            # Vaccination lasts for 100 turns (can be adjusted)
            expiry = world_obj.turnNo + 100
            if self.vaccination_expiry.get(d_id, 0) < expiry:
                self.vaccination_expiry[d_id] = expiry
                print("Agent {} was vaccinated against {} (immunity until turn {}).".format(
                    self.id, disease_name(d_id), expiry
                ))

    def has_higher_paying_job(self, world_obj):
        """Return whether a reachable, untried opening pays more than this agent's job."""
        return any(
            len(holders) < world_obj.job_capacities[location]
            and self.can_apply_for_type(world_obj.grid[location[0]][location[1]], world_obj)
            and self.applied_buildings.get(location) != world_obj.job_opening_versions[location]
            and self.in_my_region(world_obj, location)
            for location, holders in world_obj.building_jobs.items()
        )

    def can_apply_for_type(self, building_type, world_obj):
        """Unemployed agents can apply anywhere; employees can apply for higher pay."""
        if self.job is None:
            return True
        if self.job == "Hospital job":
            return False
        current_type = world_obj.job_type(self.job)
        return (current_type is not None
                and world_obj.job_income_per_year(building_type)
                > world_obj.job_income_per_year(current_type))

    def apply_for_job(self, world_obj, building_type, building_location):
        """Apply once per opening using intelligence, willpower and health."""
        if self.age < 15:
            return False
        if not self.can_apply_for_type(building_type, world_obj):
            return False
        if not self.in_my_region(world_obj, building_location):
            return False
        opening_version = world_obj.job_opening_versions[building_location]
        if self.applied_buildings.get(building_location) == opening_version:
            return False
        self.applied_buildings[building_location] = opening_version
        if len(world_obj.building_jobs[building_location]) >= world_obj.job_capacities[building_location]:
            print("Agent {} found no open job at this building.".format(self.id))
            return False

        intelligence_score = max(0, min(100, (self.intelligence - 40) * 100 / 105))
        health_range = health_max - health_min
        health_score = (
            (self.health - health_min) * 100 / health_range if health_range else 100
        )
        weights = {
            "intelligence": 1.2,
            "willpower": 1.0,
            "mental_health": 0.8,
            "health": 0.8,
        }
        weighted_total = (
            intelligence_score * weights["intelligence"]
            + self.willpower * weights["willpower"]
            + self.mental_health * weights["mental_health"]
            + health_score * weights["health"]
        )
        application_score = weighted_total / sum(weights.values())
        minimum_score = world_obj.job_application_threshold(building_type)
        hired = application_score >= minimum_score
        job_title = world_obj.job_name(building_type)
        event = {
            "turn": world_obj.turnNo + 1,
            "agent_id": self.id,
            "building_type": building_type,
            "position": building_location,
            "score": round(application_score, 1),
            "minimum_score": minimum_score,
            "hired": hired,
            "job": job_title,
        }
        world_obj.job_application_events.append(event)
        if hired:
            previous_job = self.job
            previous_location = self.employed_at
            if previous_job is not None:
                world_obj.reopen_job(previous_location, self)
            world_obj.building_jobs[building_location].add(self.id)
            self.job = job_title
            self.employed_at = building_location
            world_obj.hiring_events.append(event.copy())
            print("Agent {} successfully got the {} at the {}!".format(
                self.id, job_title, building_names[building_type]
            ))
        else:
            print("Agent {} was not hired for the {} (score: {}; required: {}); "
                  "they will look for another eligible building.".format(
                self.id, job_title, event["score"], minimum_score
            ))
        return hired
