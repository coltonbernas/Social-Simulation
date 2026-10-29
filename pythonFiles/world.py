import json
import random
import math

try:
    from .config import grid_rows, grid_cols, building_counts
except ImportError:
    from config import grid_rows, grid_cols, building_counts

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
        return any(agent.can_buy_food() for agent in agents)

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
        """Split the grid into blocks and attach economy multipliers to each."""
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
                "row_start": block_row * self.region_block_h,
                "row_end": min(self.rows, (block_row + 1) * self.region_block_h) - 1,
                "col_start": block_col * self.region_block_w,
                "col_end": min(self.cols, (block_col + 1) * self.region_block_w) - 1,
                "wage_multiplier": vals.get("wage_multiplier", 1.0),
                "cost_multiplier": vals.get("cost_of_living_multiplier", 1.0),
            })
        for region in self.regions:
            print("Region {} '{}': rows {}-{}, cols {}-{}; wage x{}, cost of living x{}".format(
                region["id"], region["name"], region["row_start"], region["row_end"],
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