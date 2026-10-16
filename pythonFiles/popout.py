"""Animated Tk window for the social simulation."""
import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:  # Support both ``python pythonFiles/main.py`` and ``python -m pythonFiles.main``.
    from .world import World
    from .population import Population
    from .config import building_count
except ImportError:
    from world import World
    from population import Population
    from config import building_count


class SimulationWindow:
    def __init__(self, root):
        self.root = root
        root.title("Social Simulation")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        root.minsize(680, 500)
        self.world = None
        self.population = None
        self.running = False
        self.after_id = None
        self.batch_remaining = 0
        self.final_reported = False

        self.canvas = tk.Canvas(root, bg="#f3f6fa", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=14, pady=14)
        panel = ttk.Frame(root, padding=(0, 14, 14, 14))
        panel.pack(side="right", fill="y")
        self.status = ttk.Label(panel, text="", justify="left")
        self.status.pack(anchor="w", pady=(0, 10))

        controls = ttk.Frame(panel)
        controls.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(controls, text="Start", command=self.toggle_running)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)
        ttk.Button(controls, text="Step", command=self.step_once).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(controls, text="Batch size").grid(row=1, column=0, sticky="w", pady=(7, 2))
        self.batch_size = tk.StringVar(value="10")
        ttk.Entry(controls, textvariable=self.batch_size, width=7).grid(row=1, column=1, sticky="e", pady=(7, 2))
        ttk.Button(controls, text="Run batch", command=self.run_batch).grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(controls, text="Reset", command=self.reset).grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(controls, text="Export agents", command=self.export_agents).grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(controls, text="End simulation", command=self.end_simulation).grid(row=5, column=0, columnspan=2, sticky="ew", pady=2)
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Simulation log").pack(anchor="w", pady=(5, 3))
        self.log = tk.Text(panel, width=39, height=20, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        self.reset()
        self.canvas.bind("<Configure>", lambda _event: self.draw())

    def reset(self):
        self.stop()
        if self.world is not None and not self.final_reported:
            self._report_finished("Simulation ended by reset.")
        self.batch_remaining = 0
        self.final_reported = False
        self.world = World()
        self.population = Population(world_obj=self.world)
        print("World created with {} rows and {} columns, placed {} agents.".format(
            self.world.rows, self.world.cols, len(self.population.agents)
        ))
        self._set_log("New simulation created. Use Start, Step, or Run batch.")
        self.draw()

    def end_simulation(self):
        self.stop()
        self.batch_remaining = 0
        self._append_summary()
        self._report_finished("Simulation ended manually.")

    def close_window(self):
        self.stop()
        if self.world is not None and not self.final_reported:
            self._append_summary()
            self._report_finished("Simulation ended when the window was closed.")
        self.root.destroy()

    def export_agents(self):
        """Save all current agent attributes to a CSV spreadsheet."""
        path = filedialog.asksaveasfilename(
            title="Export agent attributes",
            defaultextension=".csv",
            filetypes=[("CSV spreadsheet", "*.csv"), ("All files", "*.*")],
            initialfile="agents.csv",
        )
        if not path:
            return

        agents = self.population.agents
        fieldnames = list(dict.fromkeys(
            key for agent in agents for key in vars(agent)
        ))
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output_file:
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                for agent in agents:
                    row = {}
                    for key, value in vars(agent).items():
                        row[key] = (
                            json.dumps(
                                sorted(value) if isinstance(value, set) else value,
                                ensure_ascii=False,
                            )
                            if isinstance(value, (dict, list, tuple, set))
                            else value
                        )
                    writer.writerow(row)
        except OSError as error:
            messagebox.showerror("Export failed", "Could not save the spreadsheet:\n{}".format(error))
            return

        self._append_log("Exported {} agents to {}".format(len(agents), path))
        messagebox.showinfo("Export complete", "Saved {} agent records.".format(len(agents)))

    def _set_log(self, message):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("end", message + "\n")
        self.log.configure(state="disabled")

    def _append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _finished(self):
        return (not self.world.can_accept_application(self.population.agents)
                and not self.world.has_school_activity(self.population.agents)
                or self.world.turnNo >= 10000)

    def toggle_running(self):
        if self.running:
            self.stop()
        elif not self._finished():
            self.running = True
            self.start_button.configure(text="Pause")
            self._schedule_step()

    def stop(self):
        self.running = False
        if hasattr(self, "start_button"):
            self.start_button.configure(text="Start")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _schedule_step(self):
        if self.running:
            self.after_id = self.root.after(350, self._advance)

    def run_batch(self):
        try:
            count = int(self.batch_size.get())
            if count < 1:
                raise ValueError
        except ValueError:
            self._append_log("Batch size must be a whole number greater than zero.")
            return
        self.stop()
        self.batch_remaining = count
        self.batch_start = self.world.turnNo + 1
        self.running = True
        self.start_button.configure(text="Pause")
        self._schedule_step()

    def step_once(self):
        self.stop()
        if not self._finished():
            self._advance()

    def _advance(self):
        self.after_id = None
        if self._finished():
            self.stop()
            self._report_finished()
            return
        print("Turn {}:".format(self.world.turnNo + 1))
        before_entries = len(self.world.building_entries)
        before_hires = len(self.world.hiring_events)
        before_quits = len(self.world.job_quit_events)
        before_deaths = len(self.world.death_events)
        before_school = len(self.world.school_events)
        before_diseases = len(self.world.disease_events)
        before_messages = len(self.world.communication_events)
        self.population.step_agents(self.world)
        print()
        added = self.world.building_entries[before_entries:]
        hires = self.world.hiring_events[before_hires:]
        quits = self.world.job_quit_events[before_quits:]
        deaths = self.world.death_events[before_deaths:]
        school_events = self.world.school_events[before_school:]
        disease_events = self.world.disease_events[before_diseases:]
        messages = self.world.communication_events[before_messages:]
        for event in added:
            x, y = event["position"]
            self._append_log("Turn {}: Agent {} entered type {} building at ({}, {}).".format(
                event["turn"], event["agent_id"], event["building_type"], x, y
            ))
        for event in hires:
            self._append_log("Turn {}: Agent {} got the {} (score: {}; required: {}).".format(
                event["turn"], event["agent_id"], event["job"],
                event["score"], event["minimum_score"]
            ))
        for event in quits:
            x, y = event["position"]
            self._append_log("Turn {}: Agent {} {}; the {} at ({}, {}) reopened.".format(
                event["turn"], event["agent_id"], event["reason"],
                event["job"], x, y
            ))
        for event in deaths:
            self._append_log("Turn {}: Agent {} died from {} at age {}.".format(
                event["turn"], event["agent_id"], event["cause"], event["age"]
            ))
        for event in school_events:
            if event["event"] == "enrolled":
                self._append_log("Turn {}: Agent {} enrolled in school.".format(
                    event["turn"], event["agent_id"]
                ))
            else:
                self._append_log("Turn {}: Agent {} graduated; intelligence is now {}.".format(
                    event["turn"], event["agent_id"], event["intelligence"]
                ))
        for event in disease_events:
            if event.get("source") == "natural":
                self._append_log("Turn {}: Agent {} contracted {} naturally.".format(
                    event["turn"], event["agent_id"], event["disease"]
                ))
            else:
                self._append_log("Turn {}: Agent {} caught {} from Agent {}.".format(
                    event["turn"], event["agent_id"], event["disease"],
                    event["source_id"]
                ))
        for event in messages:
            self._append_log("Turn {}: Agent {} shared information with Agent {}.".format(event["turn"], event["sender_id"], event["receiver_id"]))
        self.draw()
        if self.batch_remaining:
            self.batch_remaining -= 1
            if self.batch_remaining == 0 or self._finished():
                self._append_log("Batch complete: turns {}–{}; {} jobs remain open.".format(
                    self.batch_start, self.world.turnNo, self.world.open_jobs
                ))
                self._append_agent_wealth()
                self.population.print_batch_report(self.world, self.batch_start, self.world.turnNo)
                self.batch_remaining = 0
                self.stop()
                self._append_summary()
                if self._finished():
                    self._report_finished()
                return
        if self._finished():
            self.stop()
            self._append_summary()
            self._report_finished()
        elif self.running:
            self._schedule_step()

    def _append_summary(self):
        self._append_log("Status: {} turns, {} jobs filled, {} open.".format(
            self.world.turnNo, len(self.world.hiring_events), self.world.open_jobs
        ))
        self._append_log("Agent jobs: " + ", ".join(
            "{}: {}".format(agent.id, agent.job or "unemployed")
            for agent in self.population.agents
        ))
        self._append_log("Communications recorded: {}.".format(len(self.world.communication_events)))

    def _append_agent_wealth(self):
        self._append_log("Agent wealth: " + ", ".join(
            "{}: ${:,}".format(agent.id, agent.wealth)
            for agent in self.population.all_agents
        ))

    def _report_finished(self, reason=None):
        if self.final_reported:
            return
        self.final_reported = True
        if reason:
            print(reason)
            self._append_log(reason)
        elif self.world.open_jobs == 0:
            print("All building jobs are filled; simulation done.")
            self._append_log("All building jobs are filled; simulation done.")
        elif not self.world.can_accept_application(self.population.agents):
            print("No more agents can apply for the remaining jobs.")
            self._append_log("No more agents can apply for the remaining jobs.")
        elif self.world.turnNo >= 10000:
            print("Reached the 10000 turn limit.")
            self._append_log("Reached the 10000 turn limit.")
        self.population.print_stat_card(self.world)
        self._append_agent_wealth()
        self._append_log("Simulation finished.")

    def draw(self):
        if self.world is None:
            return
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        rows, cols = self.world.rows, self.world.cols
        cell = min(width / cols, height / rows)
        left, top = (width - cell * cols) / 2, (height - cell * rows) / 2
        palette = ["#2563eb", "#db2777", "#7c3aed", "#0891b2", "#ea580c", "#16a34a", "#ca8a04"]
        agents = {}
        for agent in self.population.agents:
            agents.setdefault((agent.pos_x, agent.pos_y), []).append(agent.id)
        for row in range(rows):
            for col in range(cols):
                x0, y0 = left + col * cell, top + row * cell
                x1, y1 = x0 + cell, y0 + cell
                canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="#d6dee8", width=1)
                building_type = self.world.grid[row][col]
                if building_type:
                    pad = cell * .18
                    colors = {
                        1: ("#f5b82e", "#ca8a04"),
                        2: ("#10b981", "#047857"),
                        3: ("#3b82f6", "#1d4ed8"),
                    }
                    color, outline = colors[building_type]
                    canvas.create_rectangle(
                        x0 + pad, y0 + pad, x1 - pad, y1 - pad,
                        fill=color, outline=outline, width=2
                    )
                    canvas.create_text(
                        (x0 + x1) / 2, (y0 + y1) / 2,
                        text=str(building_type), fill="white",
                        font=("Segoe UI", max(8, int(cell * .3)), "bold")
                    )
                agent_ids = agents.get((row, col))
                if agent_ids:
                    pad = cell * .12
                    color = palette[(agent_ids[0] - 1) % len(palette)]
                    canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline="white", width=2)
                    canvas.create_text(
                        (x0 + x1) / 2, (y0 + y1) / 2,
                        text=",".join(str(agent_id) for agent_id in agent_ids),
                        fill="white", font=("Segoe UI", max(8, int(cell * .24)), "bold")
                    )
        self.status.configure(text="Turn: {}\nOpen jobs: {} / {}\nAgents: {}".format(
            self.world.turnNo, self.world.open_jobs, building_count,
            len(self.population.agents)
        ))


def launch():
    root = tk.Tk()
    SimulationWindow(root)
    root.mainloop()
