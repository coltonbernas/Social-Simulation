import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from .theme import *
except ImportError:
    from ui.theme import *

# Shared path to the configs directory, regardless of execution environment
CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


class ConfigDialog(tk.Toplevel):
    """Modal dialog displaying sliders, entry boxes, and checkboxes in a 2-column scrollable grid."""

    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.title("Simulation Parameter Setup")

        # Open Maximized across platforms
        self.geometry("1080x900")
        self.configure(bg=BG)

        self.transient(parent)
        self.grab_set()

        self.original_config = json.loads(json.dumps(config_data))
        self.result = json.loads(json.dumps(config_data))
        self.predefined_start_var = tk.BooleanVar(
            value=bool(config_data.get("start_with_predefined_positions", False))
        )
        self.controls = {}

        # Hide window while constructing UI to eliminate loading flicker/lag
        # self.withdraw()
        self._setup_style()
        self._build_ui()
        # self.deiconify()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=(FONT, 10))
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure(
            "TButton",
            background=CARD,
            foreground=TEXT,
            borderwidth=0,
            padding=(12, 6),
            focusthickness=0,
        )
        style.map("TButton", background=[("active", BORDER)])
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#06101f",
            font=(FONT, 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        style.configure(
            "Preset.TCombobox",
            fieldbackground=PANEL,
            background=CARD,
            foreground=TEXT,
            arrowcolor=TEXT,
            borderwidth=1,
            padding=(8, 4),
            relief="solid",
        )
        style.map(
            "Preset.TCombobox",
            fieldbackground=[("readonly", PANEL), ("disabled", PANEL)],
            foreground=[("readonly", TEXT), ("disabled", MUTED)],
        )
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", BG)
        self.option_add("*TCombobox*Listbox.font", (FONT, 10))

    def _build_ui(self):
        # Header
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Configure Simulation Parameters",
            font=(FONT, 12, "bold"),
            foreground=ACCENT,
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Adjust parameters with sliders or click values to type directly. Uncheck to use default.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        tk.Checkbutton(
            header,
            text="Start with predefined positions",
            variable=self.predefined_start_var,
            bg=BG,
            fg=TEXT,
            selectcolor=PANEL,
            activebackground=BG,
            activeforeground=TEXT,
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
            font=(FONT, 9),
        ).pack(anchor="w", pady=(8, 0))

        ttk.Button(
            header,
            text="Create New Disease",
            command=self._open_disease_builder
        ).pack(side="right", anchor="n", pady=5)

        # Scrollable container setup
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=12, pady=5)

        # highlightthickness=0 & bd=0 eliminate screen tearing artifacts
        self.canvas = tk.Canvas(
            container,
            bg=PANEL,
            highlightthickness=0,
            bd=0
        )
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scroll_frame = ttk.Frame(self.canvas, style="Panel.TFrame")

        scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        canvas_window = self.canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _configure_canvas(event):
            self.canvas.itemconfig(canvas_window, width=event.width)

        self.canvas.bind("<Configure>", _configure_canvas)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Smooth Mouse Wheel Event Handler
        def _on_mousewheel(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            else:
                delta = int(-1 * (event.delta / 120))
                if delta != 0:
                    self.canvas.yview_scroll(delta * 2, "units")

        # Bind wheel strictly to the window level to eliminate lag
        self.bind_all("<MouseWheel>", _on_mousewheel)
        self.bind_all("<Button-4>", _on_mousewheel)
        self.bind_all("<Button-5>", _on_mousewheel)

        grid_state = {"row": 0, "col": 0}

        # Recursive parser reading directly from your nested JSON categories
        def parse_data(key_path, name, val):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                self._add_slider_card(scroll_frame, key_path, name, val, grid_state)
            elif isinstance(val, dict):
                # Move to the start of the next row if currently in column 1
                if grid_state["col"] == 1:
                    grid_state["row"] += 1
                    grid_state["col"] = 0

                section_lbl = tk.Label(
                    scroll_frame,
                    text=name.upper(),
                    bg=PANEL,
                    fg=ACCENT,
                    font=(FONT, 10, "bold"),
                )
                section_lbl.grid(
                    row=grid_state["row"],
                    column=0,
                    columnspan=2,
                    sticky="w",
                    padx=10,
                    pady=(16, 6)
                )
                grid_state["row"] += 1

                for sub_k, sub_v in val.items():
                    parse_data(key_path + [sub_k], sub_k, sub_v)

        scroll_frame.columnconfigure(0, weight=1, uniform="col")
        scroll_frame.columnconfigure(1, weight=1, uniform="col")

        for k, v in self.original_config.items():
            parse_data([k], k, v)

        # Force update to ensure scrollregion is calculated correctly
        scroll_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # Footer Buttons
        btn_frame = ttk.Frame(self, padding=12)
        btn_frame.pack(fill="x")

        # --- Config Management Section ---
        manage_frame = ttk.Frame(btn_frame)
        manage_frame.pack(side="left")

        ttk.Label(manage_frame, text="Presets:", style="Muted.TLabel").pack(side="left", padx=(0, 5))
        self.config_selector = ttk.Combobox(
            manage_frame,
            state="readonly",
            width=20,
            style="Preset.TCombobox",
        )
        self.config_selector.pack(side="left", padx=5)
        self._refresh_config_list()

        ttk.Button(manage_frame, text="Load", command=self._load_preset).pack(side="left", padx=2)
        ttk.Button(manage_frame, text="Save As...", command=self._save_preset).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text="Start Simulation",
            style="Accent.TButton",
            command=self._on_confirm
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            btn_frame,
            text="Use Defaults",
            command=self._on_defaults
        ).pack(side="right")

    def _add_slider_card(self, parent, key_path, name, default_val, grid_state):
        card = tk.Frame(parent, bg=CARD, padx=10, pady=8, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=grid_state["row"], column=grid_state["col"], sticky="ew", padx=6, pady=4)

        if grid_state["col"] == 1:
            grid_state["row"] += 1
            grid_state["col"] = 0
        else:
            grid_state["col"] = 1

        enabled_var = tk.BooleanVar(value=True)
        is_float = isinstance(default_val, float)

        if is_float:
            min_v, max_v = 0.0, max(1.0, default_val * 3.0)
            val_var = tk.DoubleVar(value=default_val)
        else:
            min_v, max_v = 0, max(100, int(default_val * 3))
            val_var = tk.IntVar(value=default_val)

        top_row = tk.Frame(card, bg=CARD)
        top_row.pack(fill="x", pady=(0, 4))

        chk = tk.Checkbutton(
            top_row,
            text=name.replace("_", " ").title(),
            variable=enabled_var,
            bg=CARD,
            fg=TEXT,
            selectcolor=PANEL,
            activebackground=CARD,
            activeforeground=TEXT,
            font=(FONT, 9, "bold"),
            anchor="w",
        )
        chk.pack(side="left", anchor="w")

        val_label = tk.Label(
            top_row,
            text=f"{default_val:.2f}" if is_float else f"{default_val}",
            bg=CARD,
            fg=ACCENT,
            anchor="e",
            font=(FONT, 9, "bold"),
            cursor="hand2",
        )
        val_label.pack(side="right")

        val_entry = tk.Entry(
            top_row,
            width=8,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            borderwidth=1,
            justify="right",
            font=(FONT, 9),
        )

        scale = tk.Scale(
            card,
            from_=min_v,
            to=max_v,
            orient="horizontal",
            variable=val_var,
            resolution=0.01 if is_float else 1,
            showvalue=0,
            bg=BORDER,
            fg=TEXT,
            troughcolor=PANEL,
            activebackground=ACCENT,
            sliderlength=20,
            sliderrelief="flat",
            bd=0,
            highlightthickness=0,
            state="normal",
        )
        scale.pack(fill="x", expand=True, pady=(2, 0))

        def sync_label(*_):
            if is_float:
                val_label.configure(text=f"{val_var.get():.2f}")
            else:
                val_label.configure(text=f"{val_var.get()}")

        val_var.trace_add("write", sync_label)

        def start_edit(_event):
            if not enabled_var.get():
                return
            val_label.pack_forget()
            val_entry.pack(side="right")
            val_entry.delete(0, "end")
            val_entry.insert(0, f"{val_var.get():.2f}" if is_float else f"{val_var.get()}")
            val_entry.focus_set()
            val_entry.select_range(0, "end")

        def finish_edit(_event=None):
            try:
                new_val = float(val_entry.get()) if is_float else int(val_entry.get())
                if new_val > scale.cget("to"):
                    scale.configure(to=new_val * 1.5)
                elif new_val < scale.cget("from"):
                    scale.configure(from_=min(0, new_val))
                val_var.set(new_val)
            except ValueError:
                pass
            val_entry.pack_forget()
            val_label.pack(side="right")

        val_label.bind("<Button-1>", start_edit)
        val_entry.bind("<Return>", finish_edit)
        val_entry.bind("<FocusOut>", finish_edit)

        def toggle_state():
            if enabled_var.get():
                scale.configure(state="normal", bg=BORDER, troughcolor=PANEL)
                val_label.configure(fg=ACCENT, cursor="hand2")
            else:
                scale.configure(state="disabled", bg=CARD, troughcolor=CARD)
                val_var.set(default_val)
                val_label.configure(fg=MUTED, cursor="")

        chk.configure(command=toggle_state)

        self.controls[tuple(key_path)] = {
            "enabled": enabled_var,
            "value": val_var,
            "default": default_val,
        }

    def _open_disease_builder(self):
        builder = tk.Toplevel(self)
        builder.title("Custom Disease Builder")
        builder.geometry("500x430")
        builder.configure(bg=BG)
        builder.transient(self)
        builder.grab_set()

        frame = ttk.Frame(builder, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Disease Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Pattern (0/1 up to 50):").grid(row=1, column=0, sticky="w", pady=5)
        pattern_entry = ttk.Entry(frame)
        pattern_entry.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Set contagiousness using:").grid(row=2, column=0, sticky="w", pady=5)
        mode_var = tk.StringVar(value="probability")
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=2, column=1, sticky="w", pady=5)
        ttk.Radiobutton(
            mode_frame, text="Per-contact probability", variable=mode_var,
            value="probability",
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame, text="R0 value", variable=mode_var, value="r0",
        ).pack(anchor="w")

        probability_input_label = ttk.Label(frame, text="Per-contact probability (0-1):")
        probability_input_label.grid(row=3, column=0, sticky="w", pady=5)
        contag_var = tk.DoubleVar(value=0.5)
        contag_scale = tk.Scale(
            frame, from_=0.0, to=1.0, resolution=0.01, variable=contag_var,
            orient="horizontal", bg=BG, fg=TEXT, highlightthickness=0,
        )
        contag_scale.grid(row=3, column=1, sticky="ew", pady=5)

        r0_input_label = ttk.Label(frame, text="R0 (must be >= 1):")
        r0_input_label.grid(row=4, column=0, sticky="w", pady=5)
        r0_var = tk.StringVar(value="2.0")
        r0_entry = ttk.Entry(frame, textvariable=r0_var)
        r0_entry.grid(row=4, column=1, sticky="ew", pady=5)

        probability_result_label = ttk.Label(frame, text="Resulting probability:")
        probability_result_label.grid(row=5, column=0, sticky="w", pady=5)
        probability_var = tk.StringVar()
        probability_result = ttk.Label(frame, textvariable=probability_var)
        probability_result.grid(row=5, column=1, sticky="w", pady=5)

        try:
            from disease import contagiousness_from_r0, register_custom_disease, DISEASES_DIR
        except ImportError:
            from pythonFiles.disease import contagiousness_from_r0, register_custom_disease, DISEASES_DIR

        def update_probability(*_):
            if mode_var.get() == "r0":
                try:
                    probability = contagiousness_from_r0(float(r0_var.get()))
                except ValueError:
                    probability_var.set("Enter a valid R0 >= 1")
                    return
                probability_var.set("{:.2f}".format(probability))
            else:
                probability_var.set("{:.2f}".format(contag_var.get()))

        def update_mode():
            r0_mode = mode_var.get() == "r0"
            if r0_mode:
                probability_input_label.grid_remove()
                contag_scale.grid_remove()
                r0_input_label.grid()
                r0_entry.grid()
                probability_result_label.grid()
                probability_result.grid()
            else:
                probability_input_label.grid()
                contag_scale.grid()
                r0_input_label.grid_remove()
                r0_entry.grid_remove()
                probability_result_label.grid_remove()
                probability_result.grid_remove()
            update_probability()

        for radio in mode_frame.winfo_children():
            radio.configure(command=update_mode)
        r0_var.trace_add("write", update_probability)
        contag_scale.configure(command=update_probability)
        update_probability()
        update_mode()

        ttk.Label(frame, text="Health damage per turn:").grid(row=6, column=0, sticky="w", pady=5)
        damage_var = tk.StringVar(value="2")
        ttk.Entry(frame, textvariable=damage_var).grid(row=6, column=1, sticky="ew", pady=5)

        def save():
            name = name_entry.get().strip()
            pattern = pattern_entry.get().strip()
            try:
                health_damage = float(damage_var.get())
                if not 0 <= health_damage < float("inf"):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Health damage must be a number greater than or equal to 0.")
                return

            if not name:
                messagebox.showerror("Error", "Name is required.")
                return
            if not pattern or any(b not in "01" for b in pattern) or len(pattern) > 50:
                messagebox.showerror("Error", "Pattern must be binary and <= 50 bits.")
                return

            r0_estimate = None
            if mode_var.get() == "r0":
                try:
                    r0_estimate = float(r0_var.get())
                    contag = contagiousness_from_r0(r0_estimate)
                except ValueError:
                    messagebox.showerror("Error", "R0 must be a finite number greater than or equal to 1.")
                    return
            else:
                contag = contag_var.get()

            try:
                d_id = register_custom_disease(
                    name,
                    pattern,
                    contagiousness=contag if r0_estimate is None else None,
                    r0_estimate=r0_estimate,
                    health_damage_per_turn=health_damage,
                )
            except (ValueError, OSError) as error:
                messagebox.showerror("Error", str(error))
                return
            
            # Save to the current result configuration so it persists in the session
            if "Custom Diseases" not in self.result:
                self.result["Custom Diseases"] = {}
            disease_data = {
                "name": name,
                "pattern": pattern,
                "contagiousness": contag,
                "health_damage_per_turn": health_damage,
            }
            if r0_estimate is not None:
                disease_data["r0_estimate"] = r0_estimate
            self.result["Custom Diseases"][d_id] = disease_data
            
            messagebox.showinfo("Success", f"Disease '{name}' saved to {DISEASES_DIR}\\{d_id}.json and added to session!")
            builder.destroy()

        ttk.Button(frame, text="Create", command=save).grid(row=7, column=0, columnspan=2, pady=20)

    def _cleanup_bindings(self):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_confirm(self):
        self._cleanup_bindings()
        self.result["start_with_predefined_positions"] = self.predefined_start_var.get()
        
        # Ensure Custom Diseases from original_config are preserved if not overwritten
        if "Custom Diseases" in self.original_config and "Custom Diseases" not in self.result:
            self.result["Custom Diseases"] = self.original_config["Custom Diseases"]
        elif "Custom Diseases" in self.original_config and "Custom Diseases" in self.result:
            # Merge them
            for d_id, d_info in self.original_config["Custom Diseases"].items():
                if d_id not in self.result["Custom Diseases"]:
                    self.result["Custom Diseases"][d_id] = d_info

        for key_path, ctrl in self.controls.items():
            final_val = ctrl["value"].get() if ctrl["enabled"].get() else ctrl["default"]
            curr = self.result
            for k in key_path[:-1]:
                curr = curr[k]
            curr[key_path[-1]] = final_val
        self.destroy()

    def _on_defaults(self):
        """Resets the UI controls to the values present when the dialog was opened."""
        self.predefined_start_var.set(False)
        for key_path, ctrl in self.controls.items():
            # Retrieve the value from the original_config passed during __init__
            curr = self.original_config
            for k in key_path[:-1]:
                curr = curr[k]
            val = curr[key_path[-1]]

            ctrl["value"].set(val)
            ctrl["enabled"].set(True)  # Assuming we want them enabled on reset

    def _on_cancel(self):
        self._cleanup_bindings()
        self.result = json.loads(json.dumps(self.original_config))
        self.destroy()

    def _refresh_config_list(self):
        if not CONFIGS_DIR.exists():
            CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        files = [f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")]
        self.config_selector['values'] = files
        if "default.json" in files:
            self.config_selector.set("default.json")

    def _save_preset(self):
        name = filedialog.asksaveasfilename(
            initialdir=str(CONFIGS_DIR),
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if name:
            # Collect current values from UI
            current_data = json.loads(json.dumps(self.result))
            
            # Ensure Custom Diseases are included in the saved preset
            if "Custom Diseases" in self.result:
                current_data["Custom Diseases"] = self.result["Custom Diseases"]
            elif "Custom Diseases" in self.original_config:
                 current_data["Custom Diseases"] = self.original_config["Custom Diseases"]

            current_data["start_with_predefined_positions"] = self.predefined_start_var.get()
            for key_path, ctrl in self.controls.items():
                val = ctrl["value"].get()
                curr = current_data
                for k in key_path[:-1]:
                    curr = curr[k]
                curr[key_path[-1]] = val
            
            with open(name, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=4)
            self._refresh_config_list()
            self.config_selector.set(os.path.basename(name))
            self.show_toast(f"Saved: {os.path.basename(name)}")

    def _load_preset(self):
        selected = self.config_selector.get()
        if not selected:
            return
        
        path = CONFIGS_DIR / selected
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            # Update UI controls
            self.predefined_start_var.set(
                bool(loaded_data.get("start_with_predefined_positions", False))
            )
            
            # Update custom diseases in result
            if "Custom Diseases" in loaded_data:
                self.result["Custom Diseases"] = loaded_data["Custom Diseases"]
            else:
                self.result.pop("Custom Diseases", None)

            for key_path, ctrl in self.controls.items():
                curr = loaded_data
                try:
                    for k in key_path[:-1]:
                        curr = curr[k]
                    val = curr[key_path[-1]]
                    ctrl["value"].set(val)
                    ctrl["enabled"].set(True)
                except KeyError:
                    continue 
                    
            self.show_toast(f"Loaded: {selected}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def show_toast(self, message, duration=2000):
        """Displays a temporary overlay message."""
        toast = tk.Label(
            self,
            text=message,
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=10,
            highlightthickness=1,
            highlightbackground="white"
        )
        # Position toast at the bottom center of the window
        toast.place(relx=0.5, rely=0.9, anchor="s")
        
        # Schedule removal
        self.after(duration, toast.destroy)
