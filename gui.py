"""
gui.py — PAGEFRAME desktop application.

A real, mouse-clickable desktop window built with Tkinter (Python's
standard-library GUI toolkit). No browser, no HTML/CSS/JS, no terminal
raw-keyboard tricks — just a normal windowed app you double-click or run
with `python gui.py`.

Run:
    python gui.py

On Linux, Tkinter is a separate OS package from pip:
    sudo apt-get install python3-tk
On macOS / Windows, Tkinter ships with the standard python.org installer.
"""
from __future__ import annotations
import traceback
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pdf_export import PDFExporter
from engine import (
    ALGO_ORDER, ALGORITHMS, ValidationError,
    compare_all, parse_ref_string, random_refs, simulate, validate_frames,
)

# ----------------------------------------------------------------------
# Palette — same visual language as the web/terminal builds
# ----------------------------------------------------------------------
BG = "#12151c"
PANEL = "#1a1e28"
PANEL_ALT = "#20242f"
PANEL_RAISED = "#262b38"
BORDER = "#2c3140"
BORDER_SOFT = "#232734"
TEXT = "#EDE8DE"
TEXT_DIM = "#9098AC"
TEXT_FAINT = "#5b6072"
AMBER = "#E8A33D"
AMBER_DIM = "#5a4222"
RUST = "#D95F4B"
RUST_DIM = "#4a2620"
TEAL = "#5FB8B0"
TEAL_DIM = "#1e3a37"

FONT_DISPLAY = ("Georgia", 15, "bold")
FONT_HEAD = ("Helvetica", 10, "bold")
FONT_BODY = ("Helvetica", 10)
FONT_MONO = ("Courier New", 11)
FONT_MONO_BOLD = ("Courier New", 13, "bold")
FONT_SMALL = ("Helvetica", 8)


# ======================================================================
# Simulation state — thin wrapper around engine.py, no algorithm logic here
# ======================================================================

class State:
    def __init__(self):
        self.refs = parse_ref_string("7,0,1,2,0,3,0,4,2,3,0,3,2")
        self.frame_count = 3
        self.algo_key = "fifo"
        self.result = simulate(self.algo_key, self.refs, self.frame_count)
        self.cursor = -1
        self.playing = False
        self.speed = 5
        self.compare_results = None
        self.compare_best = None

    def rebuild(self):
        self.result = simulate(self.algo_key, self.refs, self.frame_count)
        self.cursor = -1
        self.playing = False

    def step_next(self) -> bool:
        if self.cursor >= len(self.result["steps"]) - 1:
            self.playing = False
            return False
        self.cursor += 1
        return True

    def step_prev(self):
        if self.cursor > -1:
            self.cursor -= 1

    def restart(self):
        self.cursor = -1
        self.playing = False

    def current_step(self):
        return self.result["steps"][self.cursor] if self.cursor >= 0 else None


# ======================================================================
# MAIN APPLICATION
# ======================================================================

class PageframeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.state = State()
        self.play_job = None

        root.title("PAGEFRAME — Page Replacement Simulator")
        root.geometry("1200x780")
        root.minsize(1020, 640)
        root.configure(bg=BG)

        self._setup_style()
        self._build_menu()

        self.notebook = ttk.Notebook(root, style="Pf.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.simulate_tab = tk.Frame(self.notebook, bg=BG)
        self.compare_tab = tk.Frame(self.notebook, bg=BG)
        self.learn_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.simulate_tab, text="  Simulate  ")
        self.notebook.add(self.compare_tab, text="  Compare  ")
        self.notebook.add(self.learn_tab, text="  Learn  ")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_simulate_tab()
        self._build_compare_tab()
        self._build_learn_tab()

        self._bind_keys()
        self.refresh_all()

    # ------------------------------------------------------------
    # Style
    # ------------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Pf.TNotebook", background=BG, borderwidth=0)
        style.configure("Pf.TNotebook.Tab", background=PANEL, foreground=TEXT_DIM,
                         padding=(14, 8), font=FONT_HEAD, borderwidth=0)
        style.map("Pf.TNotebook.Tab",
                   background=[("selected", AMBER)],
                   foreground=[("selected", "#1b140a")])

        style.configure("Pf.TFrame", background=PANEL)
        style.configure("Pf.TLabel", background=PANEL, foreground=TEXT, font=FONT_BODY)
        style.configure("PfDim.TLabel", background=PANEL, foreground=TEXT_DIM, font=FONT_SMALL)
        style.configure("PfHead.TLabel", background=PANEL, foreground=TEXT_DIM, font=FONT_HEAD)

        style.configure("Pf.TButton", background=PANEL_ALT, foreground=TEXT,
                         font=FONT_HEAD, borderwidth=1, focusthickness=0, padding=6)
        style.map("Pf.TButton", background=[("active", BORDER)], bordercolor=[("!disabled", BORDER)])

        style.configure("Primary.TButton", background=AMBER, foreground="#1b140a",
                         font=FONT_HEAD, borderwidth=0, padding=7)
        style.map("Primary.TButton", background=[("active", "#f2b459")])

        style.configure("Pf.TEntry", fieldbackground=PANEL_ALT, foreground=TEXT,
                         insertcolor=TEXT, borderwidth=1)
        style.configure("Pf.TSpinbox", fieldbackground=PANEL_ALT, foreground=TEXT,
                         arrowsize=12, borderwidth=1)
        style.configure(
            "Pf.TCombobox",
            foreground=TEXT,
            fieldbackground=PANEL_ALT,
            background=PANEL_ALT,
            borderwidth=1,
            font=("Helvetica", 12),
                padding=(8, 6),
            arrowsize=18,
        )

        style.map(
            "Pf.TCombobox",
        foreground=[
            ("readonly", TEXT),
            ("focus", TEXT),
            ("!disabled", TEXT),
        ],
        fieldbackground=[
            ("readonly", PANEL_ALT),
            ("focus", PANEL_ALT),
        ],
        background=[
            ("readonly", PANEL_ALT),
            ("focus", PANEL_ALT),
        ],
        selectforeground=[
            ("readonly", TEXT),
        ],
        selectbackground=[
            ("readonly", PANEL_ALT),
        ],
        )

        style.configure("Pf.Horizontal.TScale", background=PANEL, troughcolor=PANEL_ALT)

        style.configure("Treeview", background=PANEL_ALT, fieldbackground=PANEL_ALT,
                         foreground=TEXT, borderwidth=0, rowheight=26, font=FONT_MONO)
        style.configure("Treeview.Heading", background=PANEL_RAISED, foreground=TEXT_DIM,
                         font=FONT_HEAD, borderwidth=0)
        style.map("Treeview", background=[("selected", TEAL_DIM)], foreground=[("selected", TEXT)])

    def _build_menu(self):
        """Builds the top menu bar with improved spacing and modern styling."""
        menubar = tk.Menu(self.root, bg=PANEL, fg=TEXT, activebackground=AMBER, activeforeground="#1b140a")
        filemenu = tk.Menu(menubar, tearoff=0, bg=PANEL_ALT, fg=TEXT, activebackground=AMBER, activeforeground="#1b140a")

        filemenu.add_command(label="Import reference string...", command=self.on_import)
        filemenu.add_command(label="Export reference string...", command=self.on_export)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.root.quit)

        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def _card(self, parent, title):
        """Creates a reusable card component with better spacing and modern look."""
        outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        head = tk.Label(outer, text=title.upper(), bg=PANEL, fg=TEXT_DIM, font=FONT_HEAD, anchor="w")
        head.pack(fill="x", padx=14, pady=(10, 4))
        body = tk.Frame(outer, bg=PANEL, highlightbackground=BORDER_SOFT, highlightthickness=1)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        return outer, body

    def __init__(self, root: tk.Tk):
        """Initialize the main application with enhanced responsiveness and styling."""
        self.root = root
        self.state = State()
        self.play_job = None

        root.title("PAGEFRAME — Page Replacement Simulator")
        root.geometry("1200x780")
        root.minsize(1020, 640)
        root.configure(bg=BG)

        self._setup_style()
        self._build_menu()

        # Add padding and spacing for the notebook
        self.notebook = ttk.Notebook(root, style="Pf.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs with improved layout
        self.simulate_tab = tk.Frame(self.notebook, bg=BG)
        self.compare_tab = tk.Frame(self.notebook, bg=BG)
        self.learn_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.simulate_tab, text="  Simulate  ")
        self.notebook.add(self.compare_tab, text="  Compare  ")
        self.notebook.add(self.learn_tab, text="  Learn  ")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_simulate_tab()
        self._build_compare_tab()
        self._build_learn_tab()

        self._bind_keys()
        self.refresh_all()
    def _build_simulate_tab(self):
        tab = self.simulate_tab
        tab.grid_columnconfigure(0, weight=0, minsize=290)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_columnconfigure(2, weight=0, minsize=300)
        tab.grid_rowconfigure(0, weight=1)

        left = tk.Frame(tab, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        center = tk.Frame(tab, bg=BG)
        center.grid(row=0, column=1, sticky="nsew", padx=8)
        right = tk.Frame(tab, bg=BG)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        # ---- LEFT: reference string / frames / algorithm / random gen ----
        card, body = self._card(left, "Reference string")
        card.pack(fill="x", pady=(0, 10))
        tk.Label(body, text="Page reference sequence (comma-separated)",
                 bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w")
        self.ref_var = tk.StringVar(value=",".join(map(str, self.state.refs)))
        ref_entry = ttk.Entry(body, textvariable=self.ref_var, style="Pf.TEntry", font=FONT_MONO)
        ref_entry.pack(fill="x", pady=(4, 4))
        ref_entry.bind("<Return>", lambda e: self.on_apply_refs())
        ttk.Button(body, text="Apply", style="Pf.TButton", command=self.on_apply_refs).pack(anchor="e")
        self.ref_error_lbl = tk.Label(body, text="", bg=PANEL, fg=RUST, font=FONT_SMALL, wraplength=250, justify="left")
        self.ref_error_lbl.pack(anchor="w", pady=(4, 0))

        row = tk.Frame(body, bg=PANEL); row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text="Memory frames", bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w")
        self.frames_var = tk.IntVar(value=self.state.frame_count)
        frames_spin = ttk.Spinbox(row, from_=1, to=10, textvariable=self.frames_var, width=6,
                                   style="Pf.TSpinbox", command=self.on_apply_frames)
        frames_spin.pack(anchor="w", pady=(4, 0))
        frames_spin.bind("<Return>", lambda e: self.on_apply_frames())

        row2 = tk.Frame(body, bg=PANEL); row2.pack(fill="x", pady=(10, 0))
        ttk.Button(row2, text="Import...", style="Pf.TButton", command=self.on_import).pack(side="left")
        ttk.Button(row2, text="Export...", style="Pf.TButton", command=self.on_export).pack(side="left", padx=(6, 0))

        card, body = self._card(left, "Random generator")
        card.pack(fill="x", pady=(0, 10))
        grid = tk.Frame(body, bg=PANEL); grid.pack(fill="x")
        tk.Label(grid, text="Length", bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).grid(row=0, column=0, sticky="w")
        tk.Label(grid, text="Max page #", bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.gen_len_var = tk.IntVar(value=16)
        self.gen_max_var = tk.IntVar(value=6)
        ttk.Spinbox(grid, from_=4, to=60, textvariable=self.gen_len_var, width=6, style="Pf.TSpinbox").grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Spinbox(grid, from_=1, to=20, textvariable=self.gen_max_var, width=6, style="Pf.TSpinbox").grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(2, 0))
        tk.Label(body, text="Seed (optional)", bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w", pady=(10, 0))
        self.gen_seed_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.gen_seed_var, style="Pf.TEntry", font=FONT_MONO).pack(fill="x", pady=(4, 8))
        ttk.Button(body, text="Generate string", style="Primary.TButton", command=self.on_generate).pack(fill="x")

        card, body = self._card(left, "Algorithm")
        card.pack(fill="x")
        go_var = tk.StringVar(value=self._algo_display(ALGO_ORDER[0]))

        self.algo_var = tk.StringVar(value=self._algo_display(ALGO_ORDER[0]))

        algo_menu = tk.OptionMenu(
            body,
            self.algo_var,
            *[self._algo_display(k) for k in ALGO_ORDER],
            command=lambda value: self.on_algo_change()
            )

        # Style the button
        algo_menu.configure(
            bg=PANEL_ALT,
            fg=TEXT,
            activebackground=AMBER,
            activeforeground="#1b140a",
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            font=FONT_BODY,
            padx=8,
            pady=6,
            anchor="w",
        )

# Style the dropdown menu
        algo_menu["menu"].configure(
            bg=PANEL_ALT,
            fg=TEXT,
            activebackground=AMBER,
            activeforeground="#1b140a",
            font=FONT_BODY,
            borderwidth=0,
    )

        algo_menu.pack(fill="x", pady=(2, 0))

        algo_menu.pack(fill="x", pady=(2, 0))
        

        # ---- CENTER: stage ----
        card, body = self._card(center, "Memory stage")
        card.pack(fill="both", expand=True)

        tk.Label(body, text="reference tape", bg=PANEL, fg=TEXT_FAINT, font=FONT_SMALL).pack(anchor="w")
        self.tape_canvas = tk.Canvas(body, bg=PANEL_ALT, height=70, highlightthickness=1,
                                      highlightbackground=BORDER)
        self.tape_canvas.pack(fill="x", pady=(2, 14))
        self.tape_canvas.bind("<Configure>", lambda e: self.draw_tape())

        tk.Label(body, text="memory frames", bg=PANEL, fg=TEXT_FAINT, font=FONT_SMALL).pack(anchor="w")
        self.frames_canvas = tk.Canvas(body, bg=PANEL_ALT, height=140, highlightthickness=1,
                                        highlightbackground=BORDER)
        self.frames_canvas.pack(fill="x", pady=(2, 14))
        self.frames_canvas.bind("<Configure>", lambda e: self.draw_frames())

        self.explain_lbl = tk.Label(body, text="", bg=PANEL_ALT, fg=TEXT, font=FONT_BODY,
                                     anchor="w", justify="left", padx=12, pady=10,
                                     highlightbackground=BORDER_SOFT, highlightthickness=1, wraplength=560)
        self.explain_lbl.pack(fill="x", pady=(0, 10))

        self.progress_canvas = tk.Canvas(body, bg=BORDER, height=6, highlightthickness=0)
        self.progress_canvas.pack(fill="x", pady=(0, 14))

        transport = tk.Frame(body, bg=PANEL)
        transport.pack(fill="x")
        ttk.Button(transport, text="\u23ee Restart", style="Pf.TButton", command=self.on_restart).pack(side="left")
        ttk.Button(transport, text="\u25c0 Prev", style="Pf.TButton", command=self.on_prev).pack(side="left", padx=6)
        self.play_btn = ttk.Button(transport, text="\u25b6 Play", style="Primary.TButton", command=self.on_toggle_play)
        self.play_btn.pack(side="left")
        ttk.Button(transport, text="Next \u25b6", style="Pf.TButton", command=self.on_next).pack(side="left", padx=6)

        speed_frame = tk.Frame(transport, bg=PANEL)
        speed_frame.pack(side="right")
        tk.Label(speed_frame, text="Speed", bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(side="left", padx=(0, 6))
        self.speed_var = tk.IntVar(value=self.state.speed)
        ttk.Scale(speed_frame, from_=1, to=10, orient="horizontal", variable=self.speed_var,
                  style="Pf.Horizontal.TScale", length=110,
                  command=lambda v: setattr(self.state, "speed", int(float(v)))).pack(side="left")

        # ---- RIGHT: stats ----
        card, body = self._card(right, "Statistics")
        card.pack(fill="x", pady=(0, 10))
        stat_grid = tk.Frame(body, bg=PANEL)
        stat_grid.pack(fill="x")
        self.stat_vars = {}
        stats_def = [("total", "References"), ("hits", "Hits"), ("faults", "Faults"),
                     ("replacements", "Replacements"), ("hitratio", "Hit ratio"), ("step", "Current step")]
        for i, (key, label) in enumerate(stats_def):
            r, c = divmod(i, 2)
            box = tk.Frame(stat_grid, bg=PANEL_ALT, highlightbackground=BORDER_SOFT, highlightthickness=1)
            box.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            stat_grid.grid_columnconfigure(c, weight=1)
            color = TEAL if key == "hits" else (RUST if key == "faults" else TEXT)
            v = tk.StringVar(value="0")

            tk.Label(
                box,
                textvariable=v,
                bg=PANEL_ALT,
                fg=color,
                font=FONT_MONO_BOLD,
                ).pack(anchor="w", padx=10, pady=(6, 0))

            tk.Label(
                box,
                text=label,
                bg=PANEL_ALT,
                fg=TEXT_FAINT,
                font=FONT_SMALL,
            ).pack(anchor="w", padx=10, pady=(0, 6))

            self.stat_vars[key] = v

        tk.Label(body, text="hit ratio trend", bg=PANEL, fg=TEXT_FAINT, font=FONT_SMALL).pack(anchor="w", pady=(10, 0))
        self.trend_canvas = tk.Canvas(body, bg=PANEL_ALT, height=90, highlightthickness=1,
                                       highlightbackground=BORDER)
        self.trend_canvas.pack(fill="x", pady=(2, 0))
        self.trend_canvas.bind("<Configure>", lambda e: self.draw_trend())

        card, body = self._card(right, "About this algorithm")
        card.pack(fill="both", expand=True)
        self.algo_desc_lbl = tk.Label(body, text="", bg=PANEL, fg=TEXT_DIM, font=FONT_BODY,
                                       anchor="nw", justify="left", wraplength=270)
        self.algo_desc_lbl.pack(anchor="w", fill="both", expand=True)
        self.algo_complexity_lbl = tk.Label(body, text="", bg=PANEL, fg=TEXT_FAINT, font=FONT_MONO,
                                             anchor="w", justify="left")
        self.algo_complexity_lbl.pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------
    # COMPARE TAB
    # ------------------------------------------------------------
    def _build_compare_tab(self):
        tab = self.compare_tab
        top = tk.Frame(tab, bg=BG)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Run comparison", style="Primary.TButton",
                   command=self.on_run_compare).pack(side="left")
        self.compare_info_lbl = tk.Label(top, text="Uses the reference string and frame count from the Simulate tab.",
                                          bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
        self.compare_info_lbl.pack(side="left", padx=(12, 0))

        card, body = self._card(tab, "Results")
        card.pack(fill="x", pady=(0, 10))
        columns = ("algo", "hits", "faults", "hitratio", "faultratio", "repl")
        self.cmp_tree = ttk.Treeview(body, columns=columns, show="headings", height=6)
        headers = {"algo": "Algorithm", "hits": "Hits", "faults": "Faults",
                   "hitratio": "Hit ratio", "faultratio": "Fault ratio", "repl": "Replacements"}
        for c in columns:
            self.cmp_tree.heading(c, text=headers[c])
            self.cmp_tree.column(c, anchor="center", width=140 if c == "algo" else 110)
        self.cmp_tree.pack(fill="x")

        card, body = self._card(tab, "Fault comparison")
        card.pack(fill="both", expand=True)
        self.cmp_canvas = tk.Canvas(body, bg=PANEL_ALT, highlightthickness=1, highlightbackground=BORDER)
        self.cmp_canvas.pack(fill="both", expand=True)
        self.cmp_canvas.bind("<Configure>", lambda e: self.draw_compare_chart())

    # ------------------------------------------------------------
    # LEARN TAB
    # ------------------------------------------------------------
    CONCEPTS = [
    (
        "Page Fault",
        "A page fault occurs when the CPU requests a page that is not currently loaded into "
        "physical memory (RAM). The operating system must pause the program, locate the page "
        "on secondary storage (such as a hard disk or SSD), load it into an available frame, "
        "and then continue execution.\n\n"
        "If all memory frames are already occupied, a page replacement algorithm (such as FIFO "
        "or LRU) selects a page to remove before the new page can be loaded.\n\n"
        "A large number of page faults usually results in slower system performance."
    ),

    (
        "Locality of Reference",
        "Locality of Reference is the tendency of a program to repeatedly access the same pages "
        "or pages located close to one another.\n\n"
        "There are two main types:\n"
        "• Temporal Locality – Recently accessed pages are likely to be accessed again soon.\n"
        "• Spatial Locality – Pages located near recently accessed pages are likely to be used next.\n\n"
        "Most page replacement algorithms take advantage of this behavior to reduce page faults."
    ),

    (
        "Frame",
        "A frame is a fixed-size block of physical memory (RAM). Each frame can hold exactly "
        "one page from a process.\n\n"
        "For example, if a computer has 4 frames, only 4 pages can remain in memory at the "
        "same time. When another page needs to be loaded and all frames are full, one existing "
        "page must be replaced."
    ),

    (
        "Belady's Anomaly",
        "Belady's Anomaly is a situation where increasing the number of available memory frames "
        "actually causes more page faults instead of fewer.\n\n"
        "This unusual behavior can occur with the FIFO page replacement algorithm. Algorithms "
        "such as LRU and Optimal do not experience Belady's Anomaly."
    ),

    (
        "Thrashing",
        "Thrashing occurs when the operating system spends most of its time loading and replacing "
        "pages instead of executing the program.\n\n"
        "This usually happens when there are too few memory frames available or too many programs "
        "are competing for memory. As a result, page faults become extremely frequent and overall "
        "system performance drops significantly."
    ),

    (
        "Working Set",
        "The Working Set is the collection of pages that a process is actively using during a "
        "certain period of execution.\n\n"
        "If enough memory is allocated to keep the entire working set in RAM, page faults are "
        "reduced and the program runs efficiently. If the working set cannot fit into memory, "
        "the system may begin to thrash."
    ),
    ]

    def _build_learn_tab(self):
        tab = self.learn_tab
        canvas = tk.Canvas(tab, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        card, body = self._card(scroll_frame, "Core concepts")
        card.pack(fill="x", pady=(0, 10), padx=2)
        for name, desc in self.CONCEPTS:
            row = tk.Frame(body, bg=PANEL); row.pack(fill="x", pady=4)
            tk.Label(row, text=name, bg=PANEL, fg=AMBER, font=FONT_HEAD, width=22, anchor="w",
                     justify="left").pack(side="left", anchor="n")
            tk.Label(row, text=desc, bg=PANEL, fg=TEXT_DIM, font=FONT_BODY, wraplength=780,
                     justify="left", anchor="w").pack(side="left", fill="x", expand=True)

        card, body = self._card(scroll_frame, "Algorithm reference")
        card.pack(fill="x", padx=2, pady=(0, 10))
        for key in ALGO_ORDER:
            a = ALGORITHMS[key]
            row = tk.Frame(body, bg=PANEL); row.pack(fill="x", pady=6)
            tk.Label(row, text=f"{a['label']} \u2014 {a['name']}", bg=PANEL, fg=AMBER,
                     font=FONT_HEAD, anchor="w").pack(anchor="w")
            tk.Label(row, text=a["desc"], bg=PANEL, fg=TEXT_DIM, font=FONT_BODY,
                     wraplength=900, justify="left", anchor="w").pack(anchor="w")
            tk.Label(row, text=f"time: {a['time']}    space: {a['space']}", bg=PANEL,
                     fg=TEXT_FAINT, font=FONT_MONO).pack(anchor="w", pady=(2, 0))

    # ==============================================================
    # CANVAS DRAWING
    # ==============================================================
    def draw_tape(self):
        c = self.tape_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 70
        refs = self.state.refs
        cursor = self.state.cursor
        n = len(refs)
        window = max(4, min(n, w // 34))
        start = max(0, min(cursor - window // 2, n - window)) if n > window else 0
        end = min(n, start + window)
        cell_w = w / max(1, (end - start))
        cell_w = min(cell_w, 60)
        total_w = cell_w * (end - start)
        x0 = (w - total_w) / 2

        for i in range(start, end):
            x = x0 + (i - start) * cell_w
            cy = h / 2
            box_w, box_h = cell_w - 6, 32
            if i == cursor:
                fill, outline, fg = TEAL_DIM, TEAL, TEXT
            elif i < cursor:
                fill, outline, fg = PANEL_ALT, BORDER_SOFT, TEXT_FAINT
            else:
                fill, outline, fg = PANEL_RAISED, BORDER, TEXT
            c.create_rectangle(x + 3, cy - box_h / 2, x + 3 + box_w, cy + box_h / 2,
                                fill=fill, outline=outline, width=1.5)
            c.create_text(x + 3 + box_w / 2, cy, text=str(refs[i]), fill=fg, font=FONT_MONO)
            if i == cursor:
                tip_x = x + 3 + box_w / 2
                c.create_polygon(tip_x - 6, cy - box_h / 2 - 10, tip_x + 6, cy - box_h / 2 - 10,
                                  tip_x, cy - box_h / 2 - 2, fill=TEAL, outline="")

    def draw_frames(self):
        c = self.frames_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 140
        n = self.state.frame_count
        step = self.state.current_step()
        frame_state = step["frame_state"] if step else [None] * n
        victim_idx = step["victim_idx"] if step else -1
        kind = step["kind"] if step else None
        algo_key = self.state.algo_key

        box_w = min(110, (w - 20) / max(1, n) - 14)
        box_h = 78
        total_w = n * box_w + (n - 1) * 14
        x0 = (w - total_w) / 2
        cy = h / 2

        for i in range(n):
            x = x0 + i * (box_w + 14)
            occ = frame_state[i] if i < len(frame_state) else None
            if occ is None:
                fill, outline, fg = PANEL_RAISED, BORDER, TEXT_FAINT
                val = "\u00b7"
            else:
                fill, outline, fg = AMBER_DIM, AMBER, AMBER
                val = str(occ["page"])
                if i == victim_idx:
                    outline = TEAL if kind == "fill" else RUST
                    fill = TEAL_DIM if kind == "fill" else RUST_DIM
            c.create_rectangle(x, cy - box_h / 2, x + box_w, cy + box_h / 2,
                                fill=fill, outline=outline, width=2)
            c.create_text(x + box_w / 2, cy - 6, text=val, fill=fg, font=("Courier New", 20, "bold"))
            c.create_text(x + box_w / 2, cy + box_h / 2 - 12, text=f"F{i}", fill=TEXT_FAINT, font=FONT_SMALL)
            if algo_key == "clock" and occ is not None:
                bit = occ.get("ref_bit")
                if bit is not None:
                    bx, by = x + box_w - 12, cy - box_h / 2 + 4
                    bit_color = TEAL if bit == 1 else TEXT_FAINT
                    c.create_oval(bx - 8, by - 8, bx + 8, by + 8, outline=bit_color, width=1.5, fill=PANEL)
                    c.create_text(bx, by, text=str(bit), fill=bit_color, font=("Courier New", 8, "bold"))

    def draw_trend(self):
        c = self.trend_canvas
        c.delete("all")
        w = c.winfo_width() or 260
        h = c.winfo_height() or 90
        cursor = self.state.cursor
        if cursor < 0:
            c.create_text(w / 2, h / 2, text="no data yet", fill=TEXT_FAINT, font=FONT_SMALL)
            return
        series = [round(s["cum_hits"] / (s["index"] + 1) * 100) for s in self.state.result["steps"][:cursor + 1]]
        pad = 10
        if len(series) < 2:
            series = series * 2
        step_x = (w - 2 * pad) / (len(series) - 1)
        points = []
        for i, v in enumerate(series):
            x = pad + i * step_x
            y = h - pad - (v / 100) * (h - 2 * pad)
            points.extend([x, y])
        c.create_line(*points, fill=TEAL, width=2, smooth=True)
        c.create_text(w - 30, 12, text=f"{series[-1]}%", fill=TEAL, font=FONT_SMALL)

    def draw_compare_chart(self):
        c = self.cmp_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 200
        if not self.state.compare_results:
            c.create_text(w / 2, h / 2, text="Run a comparison to see the fault chart.",
                           fill=TEXT_FAINT, font=FONT_SMALL)
            return
        results = self.state.compare_results
        best = self.state.compare_best
        max_faults = max(r["faults"] for r in results.values()) or 1
        n = len(ALGO_ORDER)
        row_h = (h - 20) / n
        max_bar_w = w - 160
        for i, key in enumerate(ALGO_ORDER):
            r = results[key]
            y = 14 + i * row_h + row_h / 2
            is_best = key == best
            color = AMBER if is_best else TEAL
            bar_w = max_bar_w * r["faults"] / max_faults
            c.create_text(70, y, text=ALGORITHMS[key]["label"], fill=TEXT_DIM, font=FONT_HEAD, anchor="e")
            c.create_rectangle(80, y - row_h * 0.28, 80 + bar_w, y + row_h * 0.28,
                                fill=color, outline="")
            c.create_text(90 + bar_w, y, text=f"{r['faults']} faults", fill=TEXT_FAINT,
                           font=FONT_SMALL, anchor="w")

    # ==============================================================
    # RENDER / REFRESH
    # ==============================================================
    def _algo_display(self, key):
        a = ALGORITHMS[key]
        return f"{a['label']} \u2014 {a['name']}"

    def _algo_key_from_display(self, display):
        for k in ALGO_ORDER:
            if self._algo_display(k) == display:
                return k
        return "fifo"

    def refresh_all(self):
        self.draw_tape()
        self.draw_frames()
        self.draw_trend()
        self.render_explain()
        self.render_stats()
        self.render_algo_desc()
        self.render_progress()

    def render_explain(self):
        step = self.state.current_step()
        if step is None:
            self.explain_lbl.config(text="Press Play or Next to begin the simulation.", fg=TEXT)
            return
        if step["hit"]:
            text = f"HIT  \u2014  Page {step['page']} was already resident, no memory movement needed."
            color = TEAL
        elif step["kind"] == "fill":
            text = f"FAULT  \u2014  Page {step['page']} loaded into free frame F{step['victim_idx']}."
            color = RUST
        else:
            label = ALGORITHMS[self.state.algo_key]["label"]
            text = (f"FAULT  \u2014  Page {step['page']} not resident. {label} evicted page "
                     f"{step['evicted_page']} from frame F{step['victim_idx']}.")
            color = RUST
        self.explain_lbl.config(text=text, fg=color)

    def render_stats(self):
        total = len(self.state.refs)
        done = self.state.cursor + 1
        step = self.state.current_step()
        hits = step["cum_hits"] if step else 0
        faults = step["cum_faults"] if step else 0
        replacements = sum(1 for s in self.state.result["steps"][:done] if s["kind"] == "evict") if step else 0
        ratio = round(hits / done * 100) if done > 0 else 0
        self.stat_vars["total"].set(str(total))
        self.stat_vars["hits"].set(str(hits))
        self.stat_vars["faults"].set(str(faults))
        self.stat_vars["replacements"].set(str(replacements))
        self.stat_vars["hitratio"].set(f"{ratio}%")
        self.stat_vars["step"].set(f"{max(done,0)}/{total}")

    def render_progress(self):
        c = self.progress_canvas
        c.delete("all")
        w = c.winfo_width() or 900
        total = len(self.state.refs)
        done = max(self.state.cursor + 1, 0)
        frac = done / total if total else 0
        c.create_rectangle(0, 0, w * frac, 6, fill=AMBER, outline="")

    def render_algo_desc(self):
        a = ALGORITHMS[self.state.algo_key]
        self.algo_desc_lbl.config(text=f"{a['name']}\n\n{a['desc']}")
        self.algo_complexity_lbl.config(text=f"time: {a['time']}    space: {a['space']}")

    # ==============================================================
    # EVENT HANDLERS
    # ==============================================================
    def on_apply_refs(self):
        try:
            self.state.refs = parse_ref_string(self.ref_var.get())
            self.state.rebuild()
            self.ref_error_lbl.config(text="")
            self.refresh_all()
            self._sync_play_button()
        except ValidationError as e:
            self.ref_error_lbl.config(text=str(e))

    def on_apply_frames(self):
        try:
            self.state.frame_count = validate_frames(self.frames_var.get())
            self.state.rebuild()
            self.refresh_all()
            self._sync_play_button()
        except ValidationError as e:
            messagebox.showerror("Invalid frame count", str(e))
            self.frames_var.set(self.state.frame_count)

    def on_algo_change(self, event=None):
        selected = self.algo_var.get()
        self.state.algo_key = self._algo_key_from_display(self.algo_var.get())
        self.state.rebuild()
        self.refresh_all()
        self._sync_play_button()

    def on_generate(self):
        try:
            refs = random_refs(int(self.gen_len_var.get()), int(self.gen_max_var.get()),
                                self.gen_seed_var.get().strip() or None)
            self.ref_var.set(",".join(map(str, refs)))
            self.on_apply_refs()
        except (ValidationError, ValueError) as e:
            messagebox.showerror("Could not generate", str(e))

    def on_export(self):

        if self.state.result is None:
            messagebox.showwarning(
                "Nothing to Export",
                "Please run a simulation first."
            )
            return

        filename = filedialog.asksaveasfilename(

            title="Export PDF Report",

            defaultextension=".pdf",

            filetypes=[
            ("PDF File", "*.pdf")
            ],

            initialfile="PageReplacementReport.pdf",
        )

        if not filename:
            return

        try:

            algorithm_key = self.state.algo_key

            algorithm_info = ALGORITHMS[algorithm_key]

            exporter = PDFExporter(
                filename=filename,
                algorithm=algorithm_key,
                algorithm_info=algorithm_info,
                frames=self.state.frame_count,
                reference_string=self.state.refs,
                result=self.state.result,
            )

            exporter.export()

            messagebox.showinfo(

                "Export Complete",

                f"PDF report saved successfully.\n\n{filename}"

            )

        except Exception as e:
            traceback.print_exc()

            messagebox.showerror(
            "Export Failed",
            traceback.format_exc()
        )
    def on_import(self):
        path = filedialog.askopenfilename(filetypes=[("JSON or CSV", "*.json *.csv *.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path) as f:
                text = f.read()
            if path.endswith(".json"):
                obj = json.loads(text)
                self.state.refs = parse_ref_string(",".join(str(x) for x in obj["refs"]))
                if "frames" in obj:
                    self.state.frame_count = validate_frames(obj["frames"])
                    self.frames_var.set(self.state.frame_count)
                if "algorithm" in obj and obj["algorithm"] in ALGORITHMS:
                    self.state.algo_key = obj["algorithm"]
                    self.algo_var.set(self._algo_display(self.state.algo_key))
            else:
                nums = [p.strip() for p in text.replace("\n", ",").split(",") if p.strip()]
                self.state.refs = parse_ref_string(",".join(nums))
            self.ref_var.set(",".join(map(str, self.state.refs)))
            self.state.rebuild()
            self.refresh_all()
            self._sync_play_button()
        except (OSError, ValueError, KeyError, ValidationError, json.JSONDecodeError) as e:
            messagebox.showerror("Import failed", str(e))

    def on_restart(self):
        self._stop_play()
        self.state.restart()
        self.refresh_all()

    def on_prev(self):
        self._stop_play()
        self.state.step_prev()
        self.refresh_all()

    def on_next(self):
        self._stop_play()
        self.state.step_next()
        self.refresh_all()

    def on_toggle_play(self):
        if self.state.playing:
            self._stop_play()
        else:
            if self.state.cursor >= len(self.state.result["steps"]) - 1:
                self.state.restart()
            self.state.playing = True
            self._sync_play_button()
            self._tick()

    def _tick(self):
        if not self.state.playing:
            return
        moved = self.state.step_next()
        self.refresh_all()
        if not moved:
            self._stop_play()
            return
        delay = max(120, int(1100 - self.state.speed * 100))
        self.play_job = self.root.after(delay, self._tick)

    def _stop_play(self):
        self.state.playing = False
        if self.play_job is not None:
            self.root.after_cancel(self.play_job)
            self.play_job = None
        self._sync_play_button()

    def _sync_play_button(self):
        self.play_btn.config(text="\u23f8 Pause" if self.state.playing else "\u25b6 Play")

    def on_run_compare(self):
        results, best = compare_all(self.state.refs, self.state.frame_count)
        self.state.compare_results, self.state.compare_best = results, best
        self.compare_info_lbl.config(
            text=f"Comparing {len(self.state.refs)} references across {self.state.frame_count} frames \u2014 best: {ALGORITHMS[best]['label']}")

        for row in self.cmp_tree.get_children():
            self.cmp_tree.delete(row)
        for key in ALGO_ORDER:
            r = results[key]
            name = ALGORITHMS[key]["label"] + (" \u2605" if key == best else "")
            self.cmp_tree.insert("", "end", values=(
                name, r["hits"], r["faults"], f"{round(r['hit_ratio']*100)}%",
                f"{round(r['fault_ratio']*100)}%", r["replacements"]))
        self.draw_compare_chart()

    def _on_tab_changed(self, event=None):
        pass

    # ------------------------------------------------------------
    # Keyboard shortcuts (mouse is primary, these are a bonus)
    # ------------------------------------------------------------
    def _bind_keys(self):
        self.root.bind("<space>", lambda e: self.on_toggle_play())
        self.root.bind("<Right>", lambda e: self.on_next())
        self.root.bind("<Left>", lambda e: self.on_prev())
        self.root.bind("<r>", lambda e: self.on_restart())


def main():
    root = tk.Tk()
    app = PageframeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
