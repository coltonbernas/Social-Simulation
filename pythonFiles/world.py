import json
import random
import math

try:
    from .config import (grid_rows, grid_cols, building_counts,
                         type_1_income_per_turn, type_2_income_per_turn,
                         grocery_food_cost)
except ImportError:
    from config import (grid_rows, grid_cols, building_counts,
                        type_1_income_per_turn, type_2_income_per_turn,
                        grocery_food_cost)

REGION_SPLIT_ROWS = 2 #REGIONS VERTICALLY
REGION_SPLIT_COLS = 2 #REGIONES SIDE BY SIDE


class World:
    def __init__(self, config=None, rows=None, cols=None, buildings=None):
        # 1. Load config dictionary from file if not explicitly supplied
        if config is None:
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        self.config = config

        # 2. Extract world grid parameters (supports nested dict or flat JSON fallback)
        world_cfg = config.get("World Settings", config) if isinstance(config, dict) else {}
        self.rows = rows if rows is not None else world_cfg.get("rows", grid_rows)
        self.cols = cols if cols is not None else world_cfg.get("cols", grid_cols)

        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.agent_grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

        # 3. Extract building counts parameter
        if buildings is None:
            # Check nested dictionary path, flat dict path, or fallback to config.py
            raw_counts = config.get("Building Counts", config.get("building_counts", building_counts))
            requested_counts = dict(raw_counts)
        else:
            # Preserve older World(buildings=N) constructor behavior
            names = tuple(building_counts)
            requested_counts = {name: 0 for name in names}
            for index in range(buildings):
                name = names[index % len(names)]
                requested_counts[name] += 1

        self.building_count = sum(requested_counts.values())
        if self.building_count > self.rows * self.cols:
            raise ValueError("Total building count cannot exceed the number of grid cells")

        self.building_jobs = {}
        self.job_opening_versions = {}
        self.school_occupants = {}
        self.grocery_stores = set()
        self.grocery_occupants = {}
        self.hospitals = set()
        self.hospital_occupants = {}
        self.houses = {}

        self.house_events = []
        self.hospital_events = []
        self.grocery_events = []
        self.school_events = []
        self.building_entries = []
        self.job_application_events = []
        self.hiring_events = []
        self.job_quit_events = []
        self.death_events = []
        self.communication_events = []
        self.relationship_events = []
        self.birth_events = []
        self.money_transfer_events = []
        self.disease_events = []
        self.migration_events = []

        self.build_regions(config.get("Regions", {}) if isinstance(config, dict) else {})
        self.place_buildings(requested_counts)
        self.turnNo = 0

    @property
    def open_jobs(self):
        return sum(job_holder is None for job_holder in self.building_jobs.values())

    def can_accept_application(self, agents):
        return any(
            holder is None
            and any(
                agent.can_apply_for_type(self.grid[location[0]][location[1]])
                and agent.applied_buildings.get(location)
                != self.job_opening_versions[location]
                for agent in agents
            )
            for location, holder in self.building_jobs.items()
        )

    def has_school_activity(self, agents):
        return any(
            agent.schooling_at is not None or agent.can_seek_school(self)
            for agent in agents
        )

    def has_grocery_activity(self, agents):
        return any(agent.can_buy_food(self) for agent in agents)

    def reopen_job(self, location, former_holder, reason="left the job"):
        """Vacate a job and notify agents that its opening is available again."""
        if self.building_jobs.get(location) != former_holder.id:
            return False
        self.building_jobs[location] = None
        self.job_opening_versions[location] += 1
        event = {
            "turn": self.turnNo + 1,
            "agent_id": former_holder.id,
            "job": former_holder.job,
            "position": location,
            "reason": reason,
        }
        self.job_quit_events.append(event)
        print("Agent {} {}; the {} at ({}, {}) is open again. "
              "Agents previously rejected here may reapply.".format(
            former_holder.id, reason, former_holder.job,
            location[0], location[1]
        ))
        return True

    def build_regions(self, region_cfg):
        """Split the grid into blocks; each block is a region with its own economy."""
        self.region_block_h = math.ceil(self.rows / REGION_SPLIT_ROWS)
        self.region_block_w = math.ceil(self.cols / REGION_SPLIT_COLS)
        configured = [(name, vals) for name, vals in region_cfg.items()
                      if isinstance(vals, dict)]
        self.regions = []
        for index in range(REGION_SPLIT_ROWS * REGION_SPLIT_COLS):
            block_row, block_col = divmod(index, REGION_SPLIT_COLS)
            if index < len(configured):
                name, vals = configured[index]
            else:
                name, vals = "Region {}".format(index + 1), {}
            self.regions.append({
                "id": index,
                "name": name,
                "country": vals.get("country", "Country 1"),
                "block_row": block_row,
                "block_col": block_col,
                "row_start": block_row * self.region_block_h,
                "row_end": min(self.rows, (block_row + 1) * self.region_block_h) - 1,
                "col_start": block_col * self.region_block_w,
                "col_end": min(self.cols, (block_col + 1) * self.region_block_w) - 1,
                "wage_multiplier": vals.get("wage_multiplier", 1.0),
                "cost_multiplier": vals.get("cost_of_living_multiplier", 1.0),
                # Live values, refreshed by update_region_stats() every turn.
                "housing_price_factor": 1.0,
                "population": 0,
                "avg_wealth": 0.0,
                "employed": 0,
                "job_seekers": 0,
                "open_jobs": 0,
                "house_count": 0,
                "economy_score": 0.5,
                "immigrants": 0,
                "emigrants": 0,
            })
        for region in self.regions:
            print("Region {} '{}' ({}): rows {}-{}, cols {}-{}; wage x{}, cost of living x{}".format(
                region["id"], region["name"], region["country"],
                region["row_start"], region["row_end"],
                region["col_start"], region["col_end"],
                region["wage_multiplier"], region["cost_multiplier"]))

    def region_of(self, row, col):
        """Return the id of the region containing this grid cell."""
        block_row = min(row // self.region_block_h, REGION_SPLIT_ROWS - 1)
        block_col = min(col // self.region_block_w, REGION_SPLIT_COLS - 1)
        return block_row * REGION_SPLIT_COLS + block_col

    def region_cells(self, region):
        return [(r, c)
                for r in range(region["row_start"], region["row_end"] + 1)
                for c in range(region["col_start"], region["col_end"] + 1)]

    def place_buildings(self, counts):
        requested_types = []
        names_to_types = {
            "type_1_workplace": 1,
            "type_2_workplace": 2,
            "school": 3,
            "grocery_store": 4,
            "hospital": 5,
            "budget_house": 6,
            "premium_house": 7,
        }
        for name, building_type in names_to_types.items():
            if name in counts:
                requested_types.extend([building_type] * counts[name])

        # Guarantee every region gets one Type 1 workplace and one budget house.
        free_cells = {(r, c) for r in range(self.rows) for c in range(self.cols)}
        placed = []
        for region in self.regions:
            cells = [cell for cell in self.region_cells(region) if cell in free_cells]
            for wanted in (1, 6):
                if wanted in requested_types and cells:
                    requested_types.remove(wanted)
                    location = random.choice(cells)
                    cells.remove(location)
                    free_cells.discard(location)
                    placed.append((wanted, location))

        locations = random.sample(sorted(free_cells), len(requested_types))
        placed.extend(zip(requested_types, locations))

        for building_type, location in placed:
            row, col = location
            self.grid[row][col] = building_type
            if building_type == 3:
                self.school_occupants[location] = set()
            elif building_type == 4:
                self.grocery_stores.add(location)
                self.grocery_occupants[location] = set()
            elif building_type == 5:
                self.hospitals.add(location)
                self.hospital_occupants[location] = set()
            elif building_type in (6, 7):
                self.houses[location] = set()
            else:
                self.building_jobs[location] = None
                self.job_opening_versions[location] = 0

    def region_distance(self, first_id, second_id):
        """Distance between two regions, in region blocks."""
        first, second = self.regions[first_id], self.regions[second_id]
        return (abs(first["block_row"] - second["block_row"])
                + abs(first["block_col"] - second["block_col"]))

    def same_country(self, first_id, second_id):
        return self.regions[first_id]["country"] == self.regions[second_id]["country"]

    def update_region_stats(self, agents, reprice=True):
        """Refresh every region's statistics; optionally move housing prices toward demand."""
        min_age = self._setting("Migration", "min_age", 18)
        sensitivity = self._setting("Regional Economy", "price_sensitivity", 0.5)
        baseline = self._setting("Regional Economy", "baseline_people_per_house", 0.5)
        smoothing = self._setting("Regional Economy", "price_smoothing", 0.3)
        floor = self._setting("Regional Economy", "price_floor", 0.6)
        ceiling = self._setting("Regional Economy", "price_ceiling", 2.5)
        w_wage = self._setting("Regional Economy", "wage_weight", 0.4)
        w_jobs = self._setting("Regional Economy", "job_weight", 0.4)
        w_wealth = self._setting("Regional Economy", "wealth_weight", 0.2)
        wealth_ref = max(1, self._setting("Regional Economy", "wealth_reference", 1000))
        weight_total = (w_wage + w_jobs + w_wealth) or 1.0

        residents = {region["id"]: [] for region in self.regions}
        for agent in agents:
            residents[agent.region].append(agent)
        house_counts = dict.fromkeys(residents, 0)
        for location in self.houses:
            house_counts[self.region_of(*location)] += 1
        open_jobs = dict.fromkeys(residents, 0)
        for location, holder in self.building_jobs.items():
            if holder is None:
                open_jobs[self.region_of(*location)] += 1

        for region in self.regions:
            rid = region["id"]
            people = residents[rid]
            adults = [a for a in people if a.age >= min_age]
            count = len(people)
            region["population"] = count
            region["avg_wealth"] = sum(a.wealth for a in people) / count if count else 0.0
            region["employed"] = sum(1 for a in people if a.job)
            region["job_seekers"] = sum(1 for a in adults if not a.job)
            region["open_jobs"] = open_jobs[rid]
            region["house_count"] = house_counts[rid]

            if reprice:
                # Housing demand: more people per house building pushes prices up.
                demand = count / max(1, house_counts[rid])
                target = 1.0 + sensitivity * (demand - baseline)
                target = max(floor, min(ceiling, target))
                region["housing_price_factor"] += smoothing * (
                    target - region["housing_price_factor"])

            real_wage = region["wage_multiplier"] / (
                region["cost_multiplier"] * region["housing_price_factor"])
            wage_score = max(0.0, min(1.0, real_wage / 1.5))
            job_score = region["open_jobs"] / (region["open_jobs"] + region["job_seekers"] + 1.0)
            wealth_score = region["avg_wealth"] / (region["avg_wealth"] + wealth_ref)
            region["economy_score"] = (
                w_wage * wage_score + w_jobs * job_score + w_wealth * wealth_score
            ) / weight_total

    def _setting(self, category, key, fallback):
        """Read a value from the nested config.json, falling back to config.py."""
        section = self.config.get(category, {}) if isinstance(self.config, dict) else {}
        if isinstance(section, dict) and key in section:
            return section[key]
        return self.config.get(key, fallback)

    def income_for(self, job, region_id):
        if job == "Type 1 job":
            base = self._setting("Economy & Jobs", "type_1_income_per_turn", type_1_income_per_turn)
        elif job == "Type 2 job":
            base = self._setting("Economy & Jobs", "type_2_income_per_turn", type_2_income_per_turn)
        else:
            return 0
        return int(round(base * self.regions[region_id]["wage_multiplier"]))

    def house_cost(self, house_type, region_id):
        key = "budget_house_cost" if house_type == 6 else "premium_house_cost"
        base = self._setting("Economy & Jobs", key, 300 if house_type == 6 else 700)
        region = self.regions[region_id]
        return int(round(base * region["cost_multiplier"]
                         * region.get("housing_price_factor", 1.0)))

    def food_cost(self, region_id):
        base = self._setting("Grocery & Needs", "grocery_food_cost", grocery_food_cost)
        return int(round(base * self.regions[region_id]["cost_multiplier"]))

    def update_housing_prices(self, agents):
        """More people per house than average -> higher housing prices in that region."""
        sensitivity = self._setting("Migration", "housing_price_sensitivity", 0.3)
        people = [0] * len(self.regions)
        houses = [0] * len(self.regions)
        for agent in agents:
            people[agent.region] += 1
        for location in self.houses:
            houses[self.region_of(*location)] += 1
        overall = sum(people) / max(1, sum(houses))
        for region in self.regions:
            density = people[region["id"]] / max(1, houses[region["id"]])
            ratio = density / overall if overall else 1.0
            region["housing_price_factor"] = max(0.5, min(2.0, 1 + sensitivity * (ratio - 1)))