"""Animated Tk window for the social simulation."""
import tkinter as tk
from tkinter import ttk

try:  # Support both ``python pythonFiles/main.py`` and ``python -m pythonFiles.main``.
    from .world import World
    from .population import Population
    from .config import fruit_count
except ImportError:
    from world import World
    from population import Population
    from config import fruit_count


class SimulationWindow:
    def __init__(self, root):
        self.root = root
        root.title("Social Simulation")
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
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Simulation log").pack(anchor="w", pady=(5, 3))
        self.log = tk.Text(panel, width=39, height=20, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        self.reset()
        self.canvas.bind("<Configure>", lambda _event: self.draw())

    def reset(self):
        self.stop()
        self.batch_remaining = 0
        self.final_reported = False
        self.world = World()
        self.population = Population(world_obj=self.world)
        print("World created with {} rows and {} columns, placed {} agents.".format(
            self.world.rows, self.world.cols, len(self.population.agents)
        ))
        self._set_log("New simulation created. Use Start, Step, or Run batch.")
        self.draw()

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
        return self.world.fruit <= 0 or self.world.turnNo >= 10000

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
        before_pickups = len(self.world.pickup_events)
        before_messages = len(self.world.communication_events)
        self.population.step_agents(self.world)
        print()
        added = self.world.pickup_events[before_pickups:]
        messages = self.world.communication_events[before_messages:]
        for event in added:
            x, y = event["position"]
            self._append_log("Turn {}: Agent {} picked fruit at ({}, {}).".format(event["turn"], event["agent_id"], x, y))
        for event in messages:
            self._append_log("Turn {}: Agent {} shared information with Agent {}.".format(event["turn"], event["sender_id"], event["receiver_id"]))
        self.draw()
        if self.batch_remaining:
            self.batch_remaining -= 1
            if self.batch_remaining == 0 or self._finished():
                self._append_log("Batch complete: turns {}–{}; {} fruit remaining.".format(self.batch_start, self.world.turnNo, self.world.fruit))
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
        totals = {agent.id: 0 for agent in self.population.agents}
        for event in self.world.pickup_events:
            totals[event["agent_id"]] += 1
        self._append_log("Status: {} turns, {} fruit collected, {} remaining.".format(self.world.turnNo, len(self.world.pickup_events), self.world.fruit))
        self._append_log("Agent totals: " + ", ".join("{}: {}".format(agent_id, count) for agent_id, count in totals.items()))
        self._append_log("Communications recorded: {}.".format(len(self.world.communication_events)))

    def _report_finished(self):
        if self.final_reported:
            return
        self.final_reported = True
        if self.world.fruit == 0:
            print("All fruit picked up; simulation done.")
        elif self.world.turnNo >= 10000:
            print("Reached the 10000 turn limit.")
        self.population.print_stat_card(self.world)
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
        agents = {(agent.pos_x, agent.pos_y): agent.id for agent in self.population.agents}
        for row in range(rows):
            for col in range(cols):
                x0, y0 = left + col * cell, top + row * cell
                x1, y1 = x0 + cell, y0 + cell
                canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="#d6dee8", width=1)
                if self.world.grid[row][col]:
                    pad = cell * .28
                    canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill="#f5b82e", outline="#ca8a04", width=1)
                agent_id = agents.get((row, col))
                if agent_id is not None:
                    pad = cell * .12
                    color = palette[(agent_id - 1) % len(palette)]
                    canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline="white", width=2)
                    canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(agent_id), fill="white", font=("Segoe UI", max(8, int(cell * .28)), "bold"))
        self.status.configure(text="Turn: {}\nFruit remaining: {} / {}\nAgents: {}".format(self.world.turnNo, self.world.fruit, fruit_count, len(self.population.agents)))


def launch():
    root = tk.Tk()
    SimulationWindow(root)
    root.mainloop()
