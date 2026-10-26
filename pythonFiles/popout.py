import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
 
try:  # Support both ``python main.py`` and ``python -m pythonFiles.main``.
    from .world import World
    from .population import Population
    from .config import building_names
except ImportError:
    from world import World
    from population import Population
    from config import building_names
 
# ---------------------------------------------------------------- 1. theme
BG, PANEL, CARD, BORDER = "#0b1220", "#111a2e", "#1a263d", "#26344f"
TEXT, MUTED, ACCENT = "#e2e8f0", "#8b9bb4", "#38bdf8"
FONT = "Segoe UI"
 
# building type -> (fill colour, label)
BUILDINGS = {
    1: ("#f59e0b", "W1"), 2: ("#10b981", "W2"), 3: ("#3b82f6", "SCH"),
    4: ("#ef4444", "GRO"), 5: ("#a855f7", "HOS"), 6: ("#d4a373", "H1"),
    7: ("#f472b6", "H2"),
}
# what an agent is doing -> dot colour
STATUS_COLORS = {
    "Hospitalized": "#c084fc", "Sick": "#f87171", "Hungry": "#fb923c",
    "In school": "#60a5fa", "Employed": "#4ade80", "Unemployed": "#e2e8f0",
}
# log category -> text colour
LOG_COLORS = {
    "jobs": "#fbbf24", "health": "#f87171", "social": "#f472b6",
    "money": "#4ade80", "life": "#38bdf8", "info": "#cbd5e1",
}
MAX_LOG_LINES = 2000
 
 
def agent_status(agent):
    """Pick the single most important thing about an agent right now."""
    if agent.hospitalized_at is not None:
        return "Hospitalized"
    if agent.diseases:
        return "Sick"
    if agent.hunger < 25:
        return "Hungry"
    if agent.schooling_at is not None:
        return "In school"
    if agent.job:
        return "Employed"
    return "Unemployed"
 
 
class SimulationWindow:
    def __init__(self, root):
        self.root = root
        root.title("Social Simulation")
        root.geometry("1280x800")
        root.minsize(980, 620)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close_window)
 
        # Simulation state
        self.world = None
        self.population = None
        self.running = False
        self.after_id = None
        self.batch_remaining = 0
        self.batch_start = 1
        self.final_reported = False
        self.buildings = []        # cached [(row, col, type)] so drawing is fast
        self.history = {"health": [], "wealth": []}
 
        # View state
        self.view = "map"          # "map" or "wealth"
        self.selected_id = None
        self.fit = True            # auto-fit the map to the window
        self.cell = 8.0            # pixels per grid cell
        self.off_x = self.off_y = 0.0
        self._drag = None
        self._moved = False
        self._tree_guard = False
 
        self._setup_style()
        self._build_toolbar()
        self._build_body()
        self._build_status_bar()
        self.canvas.bind("<Configure>", lambda _e: self.draw())
        root.after(50, self.reset)
 
    # ------------------------------------------------------------ 2. layout
    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=(FONT, 10))
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", background=CARD, foreground=TEXT,
                        borderwidth=0, padding=(12, 6), focusthickness=0)
        style.map("TButton", background=[("active", BORDER)])
        style.configure("Accent.TButton", background=ACCENT,
                        foreground="#06101f", font=(FONT, 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        style.configure("TEntry", fieldbackground=CARD, foreground=TEXT,
                        insertcolor=TEXT, borderwidth=0)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=(14, 7), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", CARD)],
                  foreground=[("selected", ACCENT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, borderwidth=0, rowheight=24)
        style.configure("Treeview.Heading", background=CARD, foreground=MUTED,
                        borderwidth=0)
        style.map("Treeview", background=[("selected", "#1e4a6b")])
 
    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=10)
        bar.pack(fill="x")
        self.start_button = ttk.Button(bar, text="▶  Start", width=10,
                                       style="Accent.TButton",
                                       command=self.toggle_running)
        self.start_button.pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Step", command=self.step_once).pack(side="left")
 
        ttk.Label(bar, text="Batch", style="Muted.TLabel").pack(side="left", padx=(14, 4))
        self.batch_size = tk.StringVar(value="10")
        ttk.Entry(bar, textvariable=self.batch_size, width=5).pack(side="left")
        ttk.Button(bar, text="Run batch", command=self.run_batch).pack(side="left", padx=6)
 
        ttk.Label(bar, text="Speed", style="Muted.TLabel").pack(side="left", padx=(14, 4))
        self.speed = tk.DoubleVar(value=4)  # turns per second
        ttk.Scale(bar, from_=1, to=30, variable=self.speed, length=120).pack(side="left")
 
        ttk.Button(bar, text="End", command=self.end_simulation).pack(side="right")
        ttk.Button(bar, text="Export", command=self.export_agents).pack(side="right", padx=6)
        ttk.Button(bar, text="Reset", command=self.reset).pack(side="right")
 
    def _build_body(self):
        body = tk.PanedWindow(self.root, orient="horizontal", bg=BG, bd=0, sashwidth=6)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 4))
 
        # Left: map + legend
        left = ttk.Frame(body)
        body.add(left, stretch="always", minsize=500)
        top = ttk.Frame(left)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Scroll = zoom · drag = pan · click = inspect",
                  style="Muted.TLabel").pack(side="left")
        self.view_button = ttk.Button(top, text="Wealth chart", command=self.toggle_view)
        self.view_button.pack(side="right")
        ttk.Button(top, text="Fit map", command=self.fit_map).pack(side="right", padx=6)
 
        self.canvas = tk.Canvas(left, bg=BG, highlightthickness=1,
                                highlightbackground=BORDER, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", lambda e: self._zoom(e, 1.15 if e.delta > 0 else 1 / 1.15))
        self.canvas.bind("<Button-4>", lambda e: self._zoom(e, 1.15))   # Linux
        self.canvas.bind("<Button-5>", lambda e: self._zoom(e, 1 / 1.15))
        self.canvas.bind("<Motion>", self._on_hover)
 
        for items, symbol in (
                (((building_names[t], c) for t, (c, _l) in BUILDINGS.items()), "■ "),
                (STATUS_COLORS.items(), "● ")):
            row = ttk.Frame(left)
            row.pack(fill="x", pady=(4, 0))
            for name, color in items:
                tk.Label(row, text=symbol + name, bg=BG, fg=color,
                         font=(FONT, 9)).pack(side="left", padx=(0, 10))
 
        # Right: tabs
        right = ttk.Frame(body)
        body.add(right, minsize=360, width=420)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        overview = ttk.Frame(self.notebook, padding=10)
        agents = ttk.Frame(self.notebook, padding=10)
        log = ttk.Frame(self.notebook, padding=10)
        for tab, name in ((overview, "Overview"), (agents, "Agents"), (log, "Event log")):
            tab.configure(style="TFrame")
            self.notebook.add(tab, text=name)
        self._build_overview(overview)
        self._build_agents(agents)
        self._build_log(log)
 
    def _build_overview(self, tab):
        grid = tk.Frame(tab, bg=BG)
        grid.pack(fill="x")
        self.stat_values = {}
        cards = (("pop", "Population"), ("health", "Avg health"),
                 ("sick", "Sick"), ("employed", "Employed"),
                 ("wealth", "Avg wealth"), ("jobs", "Open jobs"))
        for i, (key, title) in enumerate(cards):
            card = tk.Frame(grid, bg=CARD, padx=10, pady=6)
            card.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
            tk.Label(card, text=title.upper(), bg=CARD, fg=MUTED,
                     font=(FONT, 8, "bold")).pack(anchor="w")
            label = tk.Label(card, text="–", bg=CARD, fg=TEXT, font=(FONT, 16, "bold"))
            label.pack(anchor="w")
            self.stat_values[key] = label
            grid.columnconfigure(i % 2, weight=1, uniform="c")
 
        self.sparks = {}
        for key, title, color in (("health", "Average health", "#f87171"),
                                  ("wealth", "Average wealth", "#4ade80")):
            tk.Label(tab, text=title, bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(10, 0))
            spark = tk.Canvas(tab, bg=CARD, height=70, highlightthickness=0)
            spark.pack(fill="x")
            spark.bind("<Configure>", lambda _e: self.draw_sparklines())
            self.sparks[key] = (spark, color)
 
    def _build_agents(self, tab):
        self.tree = ttk.Treeview(tab, columns=("id", "age", "hp", "wealth", "status"),
                                 show="headings", height=11, selectmode="browse")
        for col, title, width in (("id", "ID", 40), ("age", "Age", 45), ("hp", "HP", 45),
                                  ("wealth", "Wealth", 80), ("status", "Status", 100)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center", stretch=(col == "status"))
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        for status, color in STATUS_COLORS.items():
            self.tree.tag_configure(status, foreground=color)
 
        self.agent_title = tk.Label(tab, text="Select an agent", bg=BG, fg=ACCENT,
                                    font=(FONT, 13, "bold"), anchor="w")
        self.agent_title.pack(fill="x", pady=(10, 4))
        self.agent_detail = tk.Text(tab, height=12, wrap="word", bg=CARD, fg=TEXT,
                                    relief="flat", font=(FONT, 10), padx=8, pady=6,
                                    state="disabled")
        self.agent_detail.pack(fill="both", expand=True)
        self.agent_detail.tag_configure("key", foreground=MUTED)
 
    def _build_log(self, tab):
        self.log = tk.Text(tab, wrap="word", bg=PANEL, fg=TEXT, relief="flat",
                           font=("Consolas", 9), padx=8, pady=6, state="disabled")
        scroll = ttk.Scrollbar(tab, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        for category, color in LOG_COLORS.items():
            self.log.tag_configure(category, foreground=color)
 
    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=PANEL, padx=10, pady=4)
        bar.pack(fill="x", side="bottom")
        self.hover_label = tk.Label(bar, text="Hover over the map for details.",
                                    bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.hover_label.pack(side="left")
        self.turn_label = tk.Label(bar, text="", bg=PANEL, fg=ACCENT, font=(FONT, 9, "bold"))
        self.turn_label.pack(side="right")
 
    # ------------------------------------------------- 3. simulation control
    def reset(self):
        self.stop()
        if self.world is not None and not self.final_reported:
            self._report_finished("Simulation ended by reset.")
        self.batch_remaining = 0
        self.final_reported = False
        self.view = "map"
        self.view_button.configure(text="Wealth chart")
        self.selected_id = None
        self.fit = True
        self.world = World()
        self.population = Population(world_obj=self.world)
        self.buildings = [(r, c, self.world.grid[r][c])
                          for r in range(self.world.rows) for c in range(self.world.cols)
                          if self.world.grid[r][c]]
        self.history = {"health": [], "wealth": []}
        print("World created with {} rows and {} columns, placed {} agents.".format(
            self.world.rows, self.world.cols, len(self.population.agents)))
        self._clear_log()
        self._log("New simulation created. Use Start, Step, or Run batch.")
        self._record_history()
        self.refresh_panels()
        self.draw()
 
    def end_simulation(self):
        self.stop()
        self.batch_remaining = 0
        self._report_finished("Simulation ended manually.")
 
    def close_window(self):
        self.stop()
        if self.world is not None and not self.final_reported:
            self._report_finished("Simulation ended when the window was closed.")
        self.root.destroy()
 
    def _finished(self):
        return self.final_reported or not self.population.agents
 
    def toggle_running(self):
        if self.running:
            self.stop()
        elif not self._finished():
            self.running = True
            self.start_button.configure(text="⏸  Pause")
            self._schedule_step()
 
    def stop(self):
        self.running = False
        if hasattr(self, "start_button"):
            self.start_button.configure(text="▶  Start")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
 
    def _schedule_step(self):
        if self.running:
            self.after_id = self.root.after(
                max(20, int(1000 / max(1, self.speed.get()))), self._advance)
 
    def run_batch(self):
        try:
            count = int(self.batch_size.get())
            if count < 1:
                raise ValueError
        except ValueError:
            self._log("Batch size must be a whole number greater than zero.")
            return
        self.stop()
        self.batch_remaining = count
        self.batch_start = self.world.turnNo + 1
        self.running = True
        self.start_button.configure(text="⏸  Pause")
        self._schedule_step()
 
    def step_once(self):
        self.stop()
        if not self._finished():
            self._advance()
 
    def _advance(self):
        """Run one turn, then update the log, panels and map."""
        self.after_id = None
        if self._finished():
            self.stop()
            self._report_finished()
            return
        print("Turn {}:".format(self.world.turnNo + 1))
        before = self._event_counts()
        self.population.step_agents(self.world)
        print()
        self._log_new_events(before)
        self._record_history()
        self.refresh_panels()
        self.draw()
 
        if self.batch_remaining:
            self.batch_remaining -= 1
            if self.batch_remaining == 0 or self._finished():
                self._log("Batch complete: turns {}–{}; {} jobs remain open.".format(
                    self.batch_start, self.world.turnNo, self.world.open_jobs))
                self.population.print_batch_report(
                    self.world, self.batch_start, self.world.turnNo)
                self.batch_remaining = 0
                self.stop()
                if self._finished():
                    self._report_finished()
                return
        if self._finished():
            self.stop()
            self._report_finished()
        elif self.running:
            self._schedule_step()
 
    def _report_finished(self, reason=None):
        """Print the full stat card to the console and show the wealth chart."""
        if self.final_reported:
            return
        self.final_reported = True
        message = reason or "All agents have died; simulation done."
        print(message)
        self._log(message, "life")
        self.population.print_stat_card(self.world)
        gini = self.population.wealth_gini_coefficient()
        self._log("Turns: {}. Jobs filled: {}. Wealth Gini: {}.".format(
            self.world.turnNo, len(self.world.hiring_events),
            "n/a" if gini is None else "{:.3f}".format(gini)), "money")
        self.view = "wealth"
        self.view_button.configure(text="Show map")
        self.refresh_panels()
        self.draw()
 
    def export_agents(self):
        """Save every attribute of every living agent to a CSV file."""
        path = filedialog.asksaveasfilename(
            title="Export agent attributes", defaultextension=".csv",
            filetypes=[("CSV spreadsheet", "*.csv"), ("All files", "*.*")],
            initialfile="agents.csv")
        if not path:
            return
        agents = self.population.agents
        fieldnames = list(dict.fromkeys(key for a in agents for key in vars(a)))
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as out:
                writer = csv.DictWriter(out, fieldnames=fieldnames)
                writer.writeheader()
                for agent in agents:
                    writer.writerow({
                        key: json.dumps(sorted(v) if isinstance(v, set) else v,
                                        ensure_ascii=False)
                        if isinstance(v, (dict, list, tuple, set)) else v
                        for key, v in vars(agent).items()})
        except OSError as error:
            messagebox.showerror("Export failed", "Could not save the file:\n{}".format(error))
            return
        self._log("Exported {} agents to {}".format(len(agents), path))
        messagebox.showinfo("Export complete", "Saved {} agent records.".format(len(agents)))
 
    # -------------------------------------------------------------- 4. log
    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
 
    def _log(self, message, category="info"):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n", category)
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:  # keep the widget fast on long runs
            self.log.delete("1.0", "{}.0".format(lines - MAX_LOG_LINES))
        self.log.see("end")
        self.log.configure(state="disabled")
 
    EVENT_LISTS = (
        "building_entries", "hiring_events", "job_quit_events", "death_events",
        "school_events", "grocery_events", "disease_events", "relationship_events",
        "birth_events", "money_transfer_events", "house_events", "hospital_events",
    )
 
    def _event_counts(self):
        return {name: len(getattr(self.world, name)) for name in self.EVENT_LISTS}
 
    def _log_new_events(self, before):
        """Turn the events added during the last turn into coloured log lines."""
        def new(name):
            return getattr(self.world, name)[before[name]:]
 
        for e in new("hiring_events"):
            self._log("Turn {}: Agent {} got the {} (score {}, needed {}).".format(
                e["turn"], e["agent_id"], e["job"], e["score"], e["minimum_score"]), "jobs")
        for e in new("job_quit_events"):
            self._log("Turn {}: Agent {} {}; the {} reopened.".format(
                e["turn"], e["agent_id"], e["reason"], e["job"]), "jobs")
        for e in new("disease_events"):
            how = "naturally" if e.get("source") == "natural" else "from Agent {}".format(e["source_id"])
            self._log("Turn {}: Agent {} caught {} {}.".format(
                e["turn"], e["agent_id"], e["disease"], how), "health")
        for e in new("hospital_events"):
            self._log("Turn {}: Agent {} admitted to hospital with {}.".format(
                e["admitted_turn"], e["agent_id"], ", ".join(e["diseases"])), "health")
        for e in new("school_events"):
            text = ("enrolled in school" if e["event"] == "enrolled"
                    else "graduated (intelligence {})".format(e["intelligence"]))
            self._log("Turn {}: Agent {} {}.".format(e["turn"], e["agent_id"], text), "info")
        for e in new("grocery_events"):
            self._log("Turn {}: Agent {} bought food for ${:,}.".format(
                e["turn"], e["agent_id"], e["cost"]), "money")
        for e in new("money_transfer_events"):
            self._log("Turn {}: {} gave ${:,} to {} ({}).".format(
                e["turn"], e["from_name"], e["amount"], e["to_name"], e["reason"]), "money")
        for e in new("house_events"):
            if e["event"] == "evicted":
                text = "was evicted from the {}".format(building_names[e["house_type"]])
            else:
                text = "{} the {} for ${:,}".format(
                    "bought" if e["event"] == "bought" else "paid rent for",
                    building_names[e["house_type"]], e["amount"])
            self._log("Turn {}: Agent {} {}.".format(e["turn"], e["agent_id"], text), "money")
        for e in new("relationship_events"):
            if e.get("reason"):
                self._log("Turn {}: {} and {}; {}.".format(
                    e["turn"], e["first_name"], e["second_name"], e["reason"]), "social")
            elif e["stage_changed"]:  # only log when a relationship actually changes
                self._log("Turn {}: {} and {} are now {}.".format(
                    e["turn"], e["first_name"], e["second_name"], e["stage"]), "social")
        for e in new("birth_events"):
            self._log("Turn {}: Agent {} was born to {} and {}; religion: {}.".format(
                e["turn"], e["agent_id"], *e["parent_names"], e["religion"]), "life")
        for e in new("death_events"):
            self._log("Turn {}: Agent {} died from {} at age {}.".format(
                e["turn"], e["agent_id"], e["cause"], e["age"]), "life")
 
    # ------------------------------------------------- 5. stats & side panels
    def _stats(self):
        agents = self.population.agents
        n = len(agents)
        return {
            "n": n,
            "health": sum(a.health for a in agents) / n if n else 0,
            "wealth": sum(a.wealth for a in agents) / n if n else 0,
            "sick": sum(1 for a in agents if a.diseases),
            "employed": sum(1 for a in agents if a.job),
        }
 
    def _record_history(self):
        stats = self._stats()
        self.history["health"].append(stats["health"])
        self.history["wealth"].append(stats["wealth"])
 
    def refresh_panels(self):
        s = self._stats()
        values = {
            "pop": "{} / {}".format(s["n"], len(self.population.all_agents)),
            "health": "{:.0f}".format(s["health"]),
            "sick": str(s["sick"]),
            "employed": "{} / {}".format(s["employed"], s["n"]),
            "wealth": "${:,.0f}".format(s["wealth"]),
            "jobs": "{} / {}".format(self.world.open_jobs, len(self.world.building_jobs)),
        }
        for key, text in values.items():
            self.stat_values[key].configure(text=text)
        self.turn_label.configure(text="Turn {}  ·  {} agents alive{}".format(
            self.world.turnNo, s["n"], "  ·  FINISHED" if self.final_reported else ""))
        self.draw_sparklines()
        self.refresh_agent_table()
        self.refresh_agent_detail()
 
    def draw_sparklines(self):
        for key, (spark, color) in self.sparks.items():
            data = self.history.get(key, [])
            spark.delete("all")
            w, h = max(spark.winfo_width(), 50), max(spark.winfo_height(), 20)
            if len(data) < 2:
                spark.create_text(w / 2, h / 2, text="waiting for data…",
                                  fill=MUTED, font=(FONT, 8))
                continue
            low, span, pad = min(data), (max(data) - min(data)) or 1.0, 8
            points = []
            for i, value in enumerate(data):
                points += [pad + (w - 2 * pad) * i / (len(data) - 1),
                           h - pad - (h - 2 * pad) * (value - low) / span]
            spark.create_line(*points, fill=color, width=2)
            spark.create_text(w - 6, 8, anchor="ne", fill=TEXT, font=(FONT, 8, "bold"),
                              text="{:,.0f}".format(data[-1]))
 
    def refresh_agent_table(self):
        self._tree_guard = True  # stop our own updates triggering a selection event
        try:
            existing = set(self.tree.get_children())
            for agent in self.population.all_agents:
                iid = str(agent.id)
                alive = agent in self.population.agents
                status = agent_status(agent) if alive else "Deceased"
                row = (agent.id, agent.age, agent.health,
                       "${:,}".format(agent.wealth), status)
                tags = (status,) if alive else ()
                if iid in existing:
                    self.tree.item(iid, values=row, tags=tags)
                else:
                    self.tree.insert("", "end", iid=iid, values=row, tags=tags)
            if self.selected_id is not None and str(self.selected_id) in self.tree.get_children():
                self.tree.selection_set(str(self.selected_id))
        finally:
            self._tree_guard = False
 
    def _on_tree_select(self, _event):
        selection = self.tree.selection()
        if self._tree_guard or not selection:
            return
        self.selected_id = int(selection[0])
        self.refresh_agent_detail()
        self.draw()
 
    def _find_agent(self, agent_id):
        return next((a for a in self.population.all_agents if a.id == agent_id), None)
 
    def refresh_agent_detail(self):
        detail = self.agent_detail
        detail.configure(state="normal")
        detail.delete("1.0", "end")
        agent = self._find_agent(self.selected_id) if self.selected_id else None
        if agent is None:
            self.agent_title.configure(text="Select an agent")
            detail.insert("end", "Click an agent on the map or a row in the table.")
            detail.configure(state="disabled")
            return
        status = agent_status(agent) if agent in self.population.agents else "Deceased"
        self.agent_title.configure(text="{}  ·  {}".format(agent.name, status),
                                   fg=STATUS_COLORS.get(status, MUTED))
        fields = (
            ("Age", "{} (dies naturally at {})".format(agent.age, agent.death_age)),
            ("Health", "{}/100".format(agent.health)),
            ("Mental health", "{}/100".format(agent.mental_health)),
            ("Food", "{}/{}".format(agent.hunger, agent.hunger_max)),
            ("Wealth", "${:,}".format(agent.wealth)),
            ("Job", agent.job or "unemployed"),
            ("Home", "({}, {})".format(*agent.house) if agent.house else "homeless"),
            ("Position", "({}, {})".format(agent.pos_x, agent.pos_y)),
            ("Diseases", ", ".join(sorted(agent.diseases)) or "none"),
            ("Intelligence / willpower", "{} / {}".format(agent.intelligence, agent.willpower)),
            ("Dating", "Agent {}".format(agent.dating_partner_id)
             if agent.dating_partner_id else "single"),
            ("Children", ", ".join(str(c) for c in sorted(agent.children_ids)) or "none"),
        )
        for key, value in fields:
            detail.insert("end", key + ": ", "key")
            detail.insert("end", value + "\n")
        detail.configure(state="disabled")
 
    # ----------------------------------------------------- 6. map interaction
    def fit_map(self):
        self.fit = True
        self.view = "map"
        self.view_button.configure(text="Wealth chart")
        self.draw()
 
    def toggle_view(self):
        self.view = "wealth" if self.view == "map" else "map"
        self.view_button.configure(text="Show map" if self.view == "wealth" else "Wealth chart")
        self.draw()
 
    def _zoom(self, event, factor):
        """Zoom around the mouse pointer so the point under it stays put."""
        if self.view != "map" or self.world is None:
            return
        new_cell = max(3.0, min(90.0, self.cell * factor))
        world_x = (event.x - self.off_x) / self.cell
        world_y = (event.y - self.off_y) / self.cell
        self.cell = new_cell
        self.off_x = event.x - world_x * new_cell
        self.off_y = event.y - world_y * new_cell
        self.fit = False
        self.draw()
 
    def _on_press(self, event):
        self._drag = (event.x, event.y)
        self._moved = False
 
    def _on_drag(self, event):
        if self._drag is None or self.view != "map":
            return
        dx, dy = event.x - self._drag[0], event.y - self._drag[1]
        if abs(dx) + abs(dy) > 3:
            self._moved = True
        if self._moved:
            self.off_x += dx
            self.off_y += dy
            self._drag = (event.x, event.y)
            self.fit = False
            self.draw()
 
    def _on_release(self, event):
        if not self._moved and self.view == "map":
            self._select_at(event.x, event.y)  # a click, not a drag
        self._drag = None
 
    def _cell_at(self, x, y):
        return int((y - self.off_y) // self.cell), int((x - self.off_x) // self.cell)
 
    def _agents_at(self, row, col):
        return [a for a in self.population.agents if (a.pos_x, a.pos_y) == (row, col)]
 
    def _select_at(self, x, y):
        row, col = self._cell_at(x, y)
        found = self._agents_at(row, col)
        for d_row in (-1, 0, 1):          # be forgiving: also check neighbours
            for d_col in (-1, 0, 1):
                found = found or self._agents_at(row + d_row, col + d_col)
        self.selected_id = found[0].id if found else None
        if found:
            self.notebook.select(1)       # jump to the Agents tab
        self.refresh_agent_table()
        self.refresh_agent_detail()
        self.draw()
 
    def _on_hover(self, event):
        if self.world is None or self.view != "map":
            return
        row, col = self._cell_at(event.x, event.y)
        if not (0 <= row < self.world.rows and 0 <= col < self.world.cols):
            self.hover_label.configure(text="Hover over the map for details.")
            return
        text = "({}, {})".format(row, col)
        building = self.world.grid[row][col]
        if building:
            text += "  ·  " + building_names[building]
            if building in (1, 2):
                holder = self.world.building_jobs.get((row, col))
                text += "  ·  " + ("Agent {} works here".format(holder) if holder else "job open")
        agents = self._agents_at(row, col)
        if agents:
            text += "  ·  " + ", ".join(
                "Agent {} ({})".format(a.id, agent_status(a)) for a in agents)
        self.hover_label.configure(text=text)
 
    # ---------------------------------------------------------- 7. drawing
    def draw(self):
        if self.world is None:
            return
        if self.view == "wealth":
            self._draw_wealth_chart()
        else:
            self._draw_map()
 
    def _draw_map(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        rows, cols = self.world.rows, self.world.cols
        if self.fit:  # largest square cells that fit, centred
            self.cell = max(2.0, min(width / cols, height / rows))
            self.off_x = (width - self.cell * cols) / 2
            self.off_y = (height - self.cell * rows) / 2
        cell, ox, oy = self.cell, self.off_x, self.off_y
 
        canvas.create_rectangle(ox, oy, ox + cell * cols, oy + cell * rows,
                                fill="#0e1729", outline=BORDER)
        if cell >= 12:  # grid lines only when zoomed in enough to be useful
            for i in range(cols + 1):
                canvas.create_line(ox + i * cell, oy, ox + i * cell, oy + rows * cell, fill="#16223a")
            for i in range(rows + 1):
                canvas.create_line(ox, oy + i * cell, ox + cols * cell, oy + i * cell, fill="#16223a")
 
        pad = cell * 0.12 if cell >= 9 else 0
        for row, col, kind in self.buildings:
            x0, y0 = ox + col * cell, oy + row * cell
            if x0 > width or y0 > height or x0 + cell < 0 or y0 + cell < 0:
                continue  # off-screen
            color, label = BUILDINGS[kind]
            canvas.create_rectangle(x0 + pad, y0 + pad, x0 + cell - pad, y0 + cell - pad,
                                    fill=color, outline="")
            if cell >= 15:
                canvas.create_text(x0 + cell / 2, y0 + cell / 2, text=label, fill=BG,
                                   font=(FONT, max(7, int(cell * 0.28)), "bold"))
 
        selected = self._find_agent(self.selected_id) if self.selected_id else None
        by_cell = {}
        for agent in self.population.agents:
            by_cell.setdefault((agent.pos_x, agent.pos_y), []).append(agent)
        radius = max(3.5, cell * 0.32)
        for (row, col), group in by_cell.items():
            cx, cy = ox + (col + 0.5) * cell, oy + (row + 0.5) * cell
            if cx < -cell or cy < -cell or cx > width + cell or cy > height + cell:
                continue
            is_selected = selected in group
            if is_selected:  # dashed ring so the chosen agent is easy to find
                canvas.create_oval(cx - radius * 2.2, cy - radius * 2.2,
                                   cx + radius * 2.2, cy + radius * 2.2,
                                   outline=ACCENT, width=2, dash=(3, 3))
            canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                               fill=STATUS_COLORS[agent_status(group[0])],
                               outline="#ffffff" if is_selected else BG, width=2)
            if len(group) > 1:
                canvas.create_text(cx + radius, cy - radius, text=str(len(group)),
                                   fill=TEXT, font=(FONT, 8, "bold"))
        if not self.population.agents:
            canvas.create_text(width / 2, 30, text="All agents have died.",
                               fill="#f87171", font=(FONT, 14, "bold"))
 
    def _draw_wealth_chart(self):
        """Lorenz curve of final wealth (the further from the diagonal, the more unequal)."""
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        wealth = sorted(max(0, a.wealth) for a in self.population.all_agents)
        canvas.create_text(width / 2, 24, text="Wealth Inequality",
                           font=(FONT, 16, "bold"), fill=TEXT)
        if not wealth:
            canvas.create_text(width / 2, height / 2, text="No agent wealth data.",
                               font=(FONT, 11), fill=MUTED)
            return
        gini = self.population.wealth_gini_coefficient()
        canvas.create_text(width / 2, 48, text="Gini coefficient: {:.3f}".format(gini),
                           font=(FONT, 11), fill=MUTED)
        left, right, top, bottom = 76, width - 36, 80, height - 60
        for tick in range(6):
            share = tick / 5
            x, y = left + share * (right - left), bottom - share * (bottom - top)
            canvas.create_line(x, top, x, bottom, fill="#16223a")
            canvas.create_line(left, y, right, y, fill="#16223a")
            canvas.create_text(left - 10, y, text="{}%".format(tick * 20), anchor="e",
                               font=(FONT, 9), fill=MUTED)
            canvas.create_text(x, bottom + 16, text="{}%".format(tick * 20),
                               font=(FONT, 9), fill=MUTED)
        canvas.create_line(left, bottom, right, top, fill="#64748b", width=2, dash=(5, 4))
        total, running, points = sum(wealth), 0, [left, bottom]
        for i, value in enumerate(wealth, start=1):
            running += value
            share = running / total if total else i / len(wealth)
            points += [left + (i / len(wealth)) * (right - left),
                       bottom - share * (bottom - top)]
        canvas.create_line(*points, fill=ACCENT, width=3)
        canvas.create_text(width / 2, height - 24, text="Cumulative share of agents",
                           font=(FONT, 10), fill=MUTED)
        canvas.create_text(18, height / 2, text="Cumulative wealth", angle=90,
                           font=(FONT, 10), fill=MUTED)
 
 
def launch():
    root = tk.Tk()
    SimulationWindow(root)
    root.mainloop()
