import random
try:
    from .config import grid_rows, grid_cols, building_count
except ImportError:
    from config import grid_rows, grid_cols, building_count

class World:
    def __init__(self, rows=grid_rows, cols=grid_cols, buildings=building_count):
        self.rows = rows
        self.cols = cols
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.agent_grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.building_count = buildings
        self.building_jobs = {}
        self.job_opening_versions = {}
        self.school_occupants = {}
        self.grocery_stores = set()
        self.grocery_occupants = {}
        self.hospitals = set()
        self.hospital_occupants = {}
        self.hospital_events = []
        self.grocery_events = []
        self.school_events = []
        self.building_entries = []
        self.job_application_events = []
        self.hiring_events = []
        self.job_quit_events = []
        self.death_events = []
        self.communication_events = []
        self.disease_events = []
        self.place_buildings(buildings)
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

    def place_buildings(self, count):
        placed = 0
        while placed < count:
            row = random.randint(0, self.rows - 1)
            col = random.randint(0, self.cols - 1)
            if self.grid[row][col] == 0:
                building_type = 1 + (placed % 5)
                self.grid[row][col] = building_type
                location = (row, col)
                if building_type == 3:
                    self.school_occupants[location] = set()
                elif building_type == 4:
                    self.grocery_stores.add(location)
                    self.grocery_occupants[location] = set()
                elif building_type == 5:
                    self.hospitals.add(location)
                    self.hospital_occupants[location] = set()
                else:
                    self.building_jobs[location] = None
                    self.job_opening_versions[location] = 0
                placed += 1
