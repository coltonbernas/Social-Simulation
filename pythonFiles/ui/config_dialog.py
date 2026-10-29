import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ui.theme import *


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
        self.controls = {}

        # Hide window while constructing UI to eliminate loading flicker/lag
        self.withdraw()
        self._build_ui()
        self.deiconify()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

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

        # Footer Buttons
        btn_frame = ttk.Frame(self, padding=12)
        btn_frame.pack(fill="x")
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

    def _cleanup_bindings(self):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_confirm(self):
        self._cleanup_bindings()
        for key_path, ctrl in self.controls.items():
            final_val = ctrl["value"].get() if ctrl["enabled"].get() else ctrl["default"]
            curr = self.result
            for k in key_path[:-1]:
                curr = curr[k]
            curr[key_path[-1]] = final_val
        self.destroy()

    def _on_defaults(self):
        self._cleanup_bindings()
        self.result = json.loads(json.dumps(self.original_config))
        self.destroy()

    def _on_cancel(self):
        self._cleanup_bindings()
        self.result = json.loads(json.dumps(self.original_config))
        self.destroy()