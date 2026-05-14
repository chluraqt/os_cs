# CPU Scheduling Simulator 

import tkinter as tk
from tkinter import ttk, messagebox

BG          = "#fcfcff"        
PANEL       = "#FFFFFF"         
PANEL_ALT   = "#f1f1f1"       
BORDER      = "#3a3a3d"          
ACCENT      = "#2320f1"          
ACCENT_DIM  = "#1c3ae4"        

TEXT        = "#383842"       
TEXT_MED    = "#383842"         
TEXT_DIM    = "#383842"        

BTN_DEL     = "#a32929"       
BTN_DEL_HOV = "#a32929"
RUN_BG      = "#1c3ae4"         
RUN_HOV     = "#2320f1"

IDLE_COL    = "#4a4a52"       

FONT        = ("Segoe UI",  10)
FONT_SM     = ("Segoe UI",  9)
FONT_XS     = ("Segoe UI",  8)
FONT_BOLD   = ("Segoe UI",  10, "bold")
FONT_HEAD   = ("Segoe UI",  11, "bold")
FONT_TITLE  = ("Segoe UI",  13, "bold")
FONT_MONO   = ("Consolas",   9)

# Process colors — muted enough for dark theme, distinct enough to read
PROC_COLORS = [
    "#4a90d9", "#3aaa8a", "#d4875a", "#9b72d4",
    "#d46a8a", "#4aaabe", "#6ab870", "#d4a03a",
    "#8a72c8", "#3aa0b0",
]

# SCHEDULING ALGORITHMS
# Each function receives a list of process dicts and returns (results, gantt).

def attach_results(process, ct):
    """Compute and attach CT / TAT / WT to a process dict in-place."""
    process["ct"]  = ct
    process["tat"] = ct - process["at"]
    process["wt"]  = process["tat"] - process["bt"]


def fcfs(processes):
    """First-Come, First-Served — run processes in arrival order."""
    procs = sorted(processes, key=lambda x: (x["at"], x["pid"]))
    gantt, t = [], 0
    for p in procs:
        if t < p["at"]:
            gantt.append(("IDLE", t, p["at"]))
            t = p["at"]
        start = t
        t += p["bt"]
        attach_results(p, t)
        gantt.append((p["pid"], start, t))
    return procs, gantt


def sjf(processes):
    """Shortest Job First (non-preemptive) — always pick the shortest available burst."""
    procs = [p.copy() for p in processes]
    gantt, t, done, rem = [], 0, [], procs[:]
    while rem:
        avail = [p for p in rem if p["at"] <= t]
        if not avail:
            nxt = min(p["at"] for p in rem)
            gantt.append(("IDLE", t, nxt))
            t = nxt
            continue
        sel = min(avail, key=lambda x: (x["bt"], x["at"], x["pid"]))
        rem.remove(sel)
        start = t
        t += sel["bt"]
        attach_results(sel, t)
        gantt.append((sel["pid"], start, t))
        done.append(sel)
    return done, gantt


def srt(processes):
    """Shortest Remaining Time (preemptive SJF) — tick-by-tick preemption."""
    procs = [p.copy() for p in processes]
    for p in procs:
        p["remaining"] = p["bt"]
    gantt, t, done = [], 0, []
    while len(done) < len(procs):
        avail = [p for p in procs if p["at"] <= t and p["remaining"] > 0]
        if not avail:
            t += 1
            continue
        sel = min(avail, key=lambda x: (x["remaining"], x["at"], x["pid"]))
        # Extend the last Gantt bar if the same process continues
        if gantt and gantt[-1][0] == sel["pid"]:
            gantt[-1] = (gantt[-1][0], gantt[-1][1], t + 1)
        else:
            gantt.append((sel["pid"], t, t + 1))
        sel["remaining"] -= 1
        t += 1
        if sel["remaining"] == 0:
            attach_results(sel, t)
            done.append(sel)
    return done, gantt


def round_robin(processes, tq):
    """Round Robin — rotate processes through the queue using a fixed time quantum."""
    procs = [p.copy() for p in processes]
    for p in procs:
        p["remaining"] = p["bt"]
    procs.sort(key=lambda x: x["at"])
    gantt, t, queue, done, idx = [], 0, [], [], 0

    # Seed the queue with processes that have already arrived
    while idx < len(procs) and procs[idx]["at"] <= t:
        queue.append(procs[idx])
        idx += 1

    while queue or idx < len(procs):
        if not queue:
            nxt = procs[idx]["at"]
            gantt.append(("IDLE", t, nxt))
            t = nxt
            while idx < len(procs) and procs[idx]["at"] <= t:
                queue.append(procs[idx])
                idx += 1
        cur    = queue.pop(0)
        exec_t = min(tq, cur["remaining"])
        start  = t
        t     += exec_t
        cur["remaining"] -= exec_t
        # Admit newly arrived processes before re-queuing the current one
        while idx < len(procs) and procs[idx]["at"] <= t:
            queue.append(procs[idx])
            idx += 1
        gantt.append((cur["pid"], start, t))
        if cur["remaining"] == 0:
            attach_results(cur, t)
            done.append(cur)
        else:
            queue.append(cur)
    return done, gantt


def priority_nonpreemptive(processes):
    """Priority Scheduling (non-preemptive) — lower number = higher priority."""
    procs = [p.copy() for p in processes]
    gantt, t, done, rem = [], 0, [], procs[:]
    while rem:
        avail = [p for p in rem if p["at"] <= t]
        if not avail:
            nxt = min(p["at"] for p in rem)
            gantt.append(("IDLE", t, nxt))
            t = nxt
            continue
        sel = min(avail, key=lambda x: (x["priority"], x["at"], x["pid"]))
        rem.remove(sel)
        start = t
        t += sel["bt"]
        attach_results(sel, t)
        gantt.append((sel["pid"], start, t))
        done.append(sel)
    return done, gantt


def priority_round_robin(processes, tq):
    """Priority + Round Robin — run each priority level as its own RR group."""
    procs  = [p.copy() for p in processes]
    levels = sorted(set(p["priority"] for p in procs))
    gantt, done, t = [], [], 0

    for lv in levels:
        group = [p for p in procs if p["priority"] == lv]
        for p in group:
            p["remaining"] = p["bt"]
        group.sort(key=lambda x: x["at"])
        queue, idx = [], 0
        t = max(t, group[0]["at"])
        while idx < len(group) and group[idx]["at"] <= t:
            queue.append(group[idx])
            idx += 1
        while queue or idx < len(group):
            if not queue:
                t = group[idx]["at"]
                while idx < len(group) and group[idx]["at"] <= t:
                    queue.append(group[idx])
                    idx += 1
            cur    = queue.pop(0)
            exec_t = min(tq, cur["remaining"])
            start  = t
            t     += exec_t
            cur["remaining"] -= exec_t
            while idx < len(group) and group[idx]["at"] <= t:
                queue.append(group[idx])
                idx += 1
            gantt.append((cur["pid"], start, t))
            if cur["remaining"] == 0:
                attach_results(cur, t)
                done.append(cur)
            else:
                queue.append(cur)
    return done, gantt


# MAIN APPLICATION GUI

class CPUSchedulerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CPU Scheduler")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(980, 660)
        self.geometry("1160x740")

        self.process_rows = []   # list of dicts, one per process row
        self.row_counter  = 0   # monotonic ID for PID labels

        self._setup_styles()
        self._build_ui()

        # Default demo processes
        for at, bt in [(0, 5), (2, 3), (4, 1)]:
            self._add_process_row(at=at, bt=bt)

        self._on_algo_change()

    # ── ttk widget styling ────────────────────────────────────────────────────

    def _setup_styles(self):
        """Configure ttk widget themes to match the dark palette."""
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=PANEL_ALT, background=PANEL_ALT,
                    foreground=TEXT, bordercolor=BORDER,
                    selectbackground=PANEL_ALT, selectforeground=TEXT,
                    arrowcolor=ACCENT, padding=6, relief="flat")
        s.map("TCombobox",
              fieldbackground=[("readonly", PANEL_ALT)],
              foreground=[("readonly", TEXT)])
        s.configure("TScrollbar",
                    background=PANEL, troughcolor=BG,
                    bordercolor=BORDER, arrowcolor=TEXT_DIM,
                    relief="flat")
        s.configure("Horizontal.TScrollbar",
                    background=PANEL, troughcolor=BG,
                    bordercolor=BORDER, arrowcolor=TEXT_DIM,
                    relief="flat")

    # ── Root layout: title bar + two-column body ──────────────────────────────

    def _build_ui(self):
        """Assemble the top-level title bar and left / right column layout."""
        # Narrow title bar — just label + subtle bottom border
        title_bar = tk.Frame(self, bg=PANEL, pady=0)
        title_bar.pack(fill="x")
        tk.Frame(title_bar, bg=ACCENT, height=3).pack(fill="x", side="bottom")
        tk.Label(title_bar,
                 text="Operating System Scheduling Simulator",
                 font=FONT_TITLE, bg=PANEL, fg=TEXT,
                 pady=11, padx=18).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left  = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    # ── LEFT PANEL — algorithm picker, process list, run button ──────────────

    def _build_left(self, parent):
        """Build the control panel: algo selector, time quantum, process table."""
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # ── Algorithm selection card
        algo_card = self._card(parent)
        algo_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._card_header(algo_card, "Algorithm")

        tk.Label(algo_card, text="Scheduling policy",
                 font=FONT_XS, bg=PANEL, fg=TEXT_DIM).pack(
                 anchor="w", padx=14, pady=(8, 3))

        options = [
            ("First-Come, First-Served (FCFS)",        "fcfs"),
            ("Shortest Job First — Non-Preemptive",    "sjf"),
            ("Shortest Remaining Time — Preemptive",   "srt"),
            ("Round Robin (RR)",                        "rr"),
            ("Priority Scheduling — Non-Preemptive",   "priority"),
            ("Priority + Round Robin",                  "prr"),
        ]
        self._algo_map = {o[0]: o[1] for o in options}

        self.algo_var = tk.StringVar(value=options[0][0])
        self.algo_combo = ttk.Combobox(
            algo_card, textvariable=self.algo_var,
            values=[o[0] for o in options],
            state="readonly", font=FONT_SM, width=40)
        self.algo_combo.current(0)
        self.algo_combo.pack(fill="x", padx=14, pady=(0, 10))
        self.algo_combo.bind("<<ComboboxSelected>>",
                             lambda e: self._on_algo_change())

        # Time quantum row — packed/forgotten based on selected algorithm
        self.tq_frame = tk.Frame(algo_card, bg=PANEL)
        tk.Label(self.tq_frame, text="Time quantum:",
                 font=FONT_SM, bg=PANEL, fg=TEXT_MED).pack(side="left", padx=(14, 8))
        self.tq_var = tk.IntVar(value=2)
        sb = tk.Spinbox(self.tq_frame, from_=1, to=99,
                        textvariable=self.tq_var,
                        width=5, font=FONT_MONO,
                        relief="flat", bd=0,
                        bg=PANEL_ALT, fg=TEXT,
                        buttonbackground=PANEL_ALT,
                        insertbackground=ACCENT,
                        highlightthickness=1,
                        highlightbackground=BORDER,
                        highlightcolor=ACCENT)
        sb.pack(side="left")

        # ── Process list card
        proc_card = self._card(parent)
        proc_card.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        proc_card.rowconfigure(3, weight=1)
        proc_card.columnconfigure(0, weight=1)
        self._card_header(proc_card, "Processes")

        tk.Label(proc_card,
                 text="Priority: lower number = higher priority",
                 font=FONT_XS, bg=PANEL, fg=TEXT_DIM).pack(
                 anchor="w", padx=14, pady=(6, 0))

        # Column header bar
        self.hdr_frame = tk.Frame(proc_card, bg=PANEL_ALT)
        self.hdr_frame.pack(fill="x", padx=14, pady=(8, 0))
        self._build_col_header()

        # Scrollable process rows canvas
        rows_outer = tk.Frame(proc_card, bg=PANEL)
        rows_outer.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        self.rows_canvas = tk.Canvas(rows_outer, bg=PANEL,
                                     highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(rows_outer, orient="vertical",
                             command=self.rows_canvas.yview)
        self.rows_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.rows_canvas.pack(side="left", fill="both", expand=True)

        self.rows_frame = tk.Frame(self.rows_canvas, bg=PANEL)
        self._rows_win = self.rows_canvas.create_window(
            (0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>",
            lambda e: self.rows_canvas.configure(
                scrollregion=self.rows_canvas.bbox("all")))
        self.rows_canvas.bind("<Configure>",
            lambda e: self.rows_canvas.itemconfig(
                self._rows_win, width=e.width))

        # Add / Reset buttons
        btn_bar = tk.Frame(proc_card, bg=PANEL)
        btn_bar.pack(fill="x", padx=14, pady=(2, 12))
        self._btn(btn_bar, "+ Add",
                  self._add_process_row, PANEL_ALT, TEXT).pack(
                  side="left", padx=(0, 6))
        self._btn(btn_bar, "Reset",
                  self._clear_all, PANEL_ALT, TEXT_DIM).pack(side="left")

        # ── Run simulation button — full-width, visually dominant
        run_btn = tk.Button(parent,
                            text="▶  Run Simulation",
                            font=FONT_BOLD,
                            bg=RUN_BG, fg="#111111",
                            activebackground=RUN_HOV,
                            activeforeground="#111111",
                            relief="flat", pady=12,
                            cursor="hand2",
                            command=self._run_simulation)
        run_btn.grid(row=2, column=0, sticky="ew")

    # ── RIGHT PANEL — Gantt chart + results table ─────────────────────────────

    def _build_right(self, parent):
        """Build the output panel with a scrollable canvas for simulation results."""
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        tk.Label(parent, text="Output",
                 font=FONT_HEAD, bg=BG, fg=TEXT_MED).grid(
                 row=0, column=0, sticky="w", pady=(0, 6))

        out_wrap = tk.Frame(parent, bg=BORDER, relief="flat", bd=1)
        out_wrap.grid(row=1, column=0, sticky="nsew")
        out_wrap.rowconfigure(0, weight=1)
        out_wrap.columnconfigure(0, weight=1)

        self.out_canvas = tk.Canvas(out_wrap, bg=PANEL, highlightthickness=0)
        vsb = ttk.Scrollbar(out_wrap, orient="vertical",
                             command=self.out_canvas.yview)
        self.out_canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        self.out_canvas.grid(row=0, column=0, sticky="nsew")

        self.out_inner = tk.Frame(self.out_canvas, bg=PANEL)
        self._out_win = self.out_canvas.create_window(
            (0, 0), window=self.out_inner, anchor="nw")
        self.out_inner.bind("<Configure>",
            lambda e: self.out_canvas.configure(
                scrollregion=self.out_canvas.bbox("all")))
        self.out_canvas.bind("<Configure>",
            lambda e: self.out_canvas.itemconfig(
                self._out_win, width=e.width))

        self._show_placeholder()

    # ── Shared widget factory helpers ─────────────────────────────────────────

    def _card(self, parent):
        """Return a dark-surface card frame with a subtle border."""
        return tk.Frame(parent, bg=PANEL, relief="flat",
                        highlightthickness=1, highlightbackground=BORDER)

    def _card_header(self, parent, text):
        """Render a compact section label with a left accent strip."""
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(12, 2))
        tk.Frame(row, bg=ACCENT, width=3).pack(side="left", fill="y", padx=(0, 8))
        tk.Label(row, text=text.upper(),
                 font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=ACCENT).pack(side="left", anchor="w")

    def _btn(self, parent, text, cmd, bg, fg):
        """Factory for flat-style utility buttons."""
        return tk.Button(parent, text=text, font=FONT_SM,
                         bg=bg, fg=fg, relief="flat",
                         padx=12, pady=6, cursor="hand2",
                         activebackground=BORDER,
                         activeforeground=TEXT,
                         command=cmd)

    # ── Column header for the process table ───────────────────────────────────

    def _build_col_header(self):
        """Rebuild column headers — called on load and whenever algo changes."""
        for w in self.hdr_frame.winfo_children():
            w.destroy()
        cols = [("PID", 44), ("Arrival", 70), ("Burst", 62)]
        if self._needs_priority():
            cols.append(("Priority", 60))
        cols.append(("", 26))
        for txt, w in cols:
            tk.Label(self.hdr_frame, text=txt,
                     font=FONT_XS,
                     bg=PANEL_ALT, fg=TEXT_DIM,
                     width=w // 7, anchor="center").pack(
                     side="left", padx=1, pady=5)

    # ── Algorithm helper queries ──────────────────────────────────────────────

    def _algo_key(self):
        """Return the short key for the currently selected algorithm."""
        return self._algo_map.get(self.algo_combo.get(), "fcfs")

    def _needs_priority(self):
        """True if the selected algorithm uses a priority column."""
        return self._algo_key() in ("priority", "prr")

    def _needs_quantum(self):
        """True if the selected algorithm needs a time quantum input."""
        return self._algo_key() in ("rr", "prr")

    def _on_algo_change(self):
        """Show / hide quantum spinner and priority column when algo changes."""
        self.tq_frame.pack_forget()
        if self._needs_quantum():
            self.tq_frame.pack(fill="x", pady=(0, 10))
        self._build_col_header()
        for row in self.process_rows:
            if self._needs_priority():
                row["pri_e"].pack(side="left", padx=2)
            else:
                row["pri_e"].pack_forget()

    # ── Process row management ────────────────────────────────────────────────

    def _add_process_row(self, at="0", bt=""):
        """Append a new editable process row to the scrollable list."""
        self.row_counter += 1
        pid    = f"P{self.row_counter}"
        row_bg = PANEL_ALT if self.row_counter % 2 == 0 else PANEL

        frame = tk.Frame(self.rows_frame, bg=row_bg, pady=4)
        frame.pack(fill="x", padx=0, pady=1)

        pid_var = tk.StringVar(value=pid)
        at_var  = tk.StringVar(value=str(at))
        bt_var  = tk.StringVar(value=str(bt))
        pri_var = tk.StringVar(value="1")

        # PID badge
        tk.Label(frame, textvariable=pid_var,
                 font=("Segoe UI", 8, "bold"),
                 bg=ACCENT_DIM, fg=TEXT,
                 width=4, anchor="center",
                 pady=3, padx=2).pack(side="left", padx=(6, 6))

        def _entry(var, w=7):
            """Return a styled entry widget bound to the given StringVar."""
            return tk.Entry(frame, textvariable=var,
                            font=FONT_MONO, width=w,
                            relief="flat", bd=0,
                            fg=TEXT, bg=PANEL_ALT if row_bg == PANEL else PANEL,
                            insertbackground=ACCENT,
                            highlightthickness=1,
                            highlightbackground=BORDER,
                            highlightcolor=ACCENT)

        at_e  = _entry(at_var, 7)
        bt_e  = _entry(bt_var, 7)
        pri_e = _entry(pri_var, 5)

        at_e.pack(side="left", padx=3)
        bt_e.pack(side="left", padx=3)

        row_data = {
            "frame":   frame,
            "pid_var": pid_var,
            "at_var":  at_var,
            "bt_var":  bt_var,
            "pri_var": pri_var,
            "pri_e":   pri_e,
        }

        if self._needs_priority():
            pri_e.pack(side="left", padx=3)

        # Delete row button
        tk.Button(frame, text="✕",
                  font=FONT_XS,
                  bg=BTN_DEL, fg=TEXT,
                  activebackground=BTN_DEL_HOV,
                  relief="flat", width=2, pady=3,
                  cursor="hand2",
                  command=lambda r=row_data: self._remove_row(r)).pack(
                  side="left", padx=(6, 4))

        self.process_rows.append(row_data)

    def _remove_row(self, row):
        """Remove a process row, enforcing a minimum of one row."""
        if len(self.process_rows) <= 1:
            messagebox.showwarning("Warning", "At least one process is required.")
            return
        row["frame"].destroy()
        self.process_rows.remove(row)

    def _clear_all(self):
        """Destroy all rows and restore the three default demo processes."""
        for r in self.process_rows:
            r["frame"].destroy()
        self.process_rows.clear()
        self.row_counter = 0
        for at, bt in [(0, 5), (2, 3), (4, 1)]:
            self._add_process_row(at=at, bt=bt)
        self._show_placeholder()

    # ── Output panel helpers ──────────────────────────────────────────────────

    def _clear_output(self):
        """Remove all widgets from the output inner frame."""
        for w in self.out_inner.winfo_children():
            w.destroy()

    def _show_placeholder(self):
        """Render the idle state message before any simulation has been run."""
        self._clear_output()
        tk.Label(self.out_inner,
                 text="Run a simulation to see results here.",
                 font=FONT_SM, bg=PANEL, fg=TEXT_DIM,
                 pady=48).pack()

    # ── Input validation + algorithm dispatch ─────────────────────────────────

    def _run_simulation(self):
        """Validate inputs, dispatch to the correct algorithm, then display results."""
        if len(self.process_rows) < 3:
            messagebox.showerror("Error", "Please add at least 3 processes.")
            return

        processes = []
        for row in self.process_rows:
            pid = row["pid_var"].get().strip()
            try:
                at = int(row["at_var"].get())
                bt = int(row["bt_var"].get())
                if bt < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Input Error",
                    f"{pid}: Arrival Time and Burst Time must be integers (BT ≥ 1).")
                return
            pri = 1
            if self._needs_priority():
                try:
                    pri = int(row["pri_var"].get())
                except ValueError:
                    messagebox.showerror("Input Error",
                        f"{pid}: Priority must be an integer.")
                    return
            processes.append({"pid": pid, "at": at, "bt": bt, "priority": pri})

        key = self._algo_key()
        tq  = self.tq_var.get()

        dispatch = {
            "fcfs":     (fcfs,                   "First-Come, First-Served (FCFS)",               [processes]),
            "sjf":      (sjf,                    "Shortest Job First — Non-Preemptive (SJF)",     [processes]),
            "srt":      (srt,                    "Shortest Remaining Time — Preemptive (SRT)",    [processes]),
            "rr":       (round_robin,             f"Round Robin (RR)  ·  Quantum = {tq}",          [processes, tq]),
            "priority": (priority_nonpreemptive, "Priority Scheduling — Non-Preemptive",          [processes]),
            "prr":      (priority_round_robin,    f"Priority + Round Robin  ·  Quantum = {tq}",   [processes, tq]),
        }
        fn, title, args = dispatch[key]
        result, gantt   = fn(*args)
        self._display_results(result, gantt, title, key)

    # ── Results renderer ──────────────────────────────────────────────────────

    def _display_results(self, procs, gantt, title, key):
        """Render the Gantt chart, process table, and summary stats to the output panel."""
        self._clear_output()

        # ── Results header
        hdr = tk.Frame(self.out_inner, bg=PANEL_ALT)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title,
                 font=FONT_BOLD, bg=PANEL_ALT, fg=TEXT,
                 pady=10, padx=16).pack(anchor="w")
        tk.Frame(self.out_inner, bg=BORDER, height=1).pack(fill="x")

        # ── Build process→color mapping for Gantt and legend
        pid_color = {}
        ci = 0
        for seg in gantt:
            p = seg[0]
            if p != "IDLE" and p not in pid_color:
                pid_color[p] = PROC_COLORS[ci % len(PROC_COLORS)]
                ci += 1

        # ── Section label — Gantt Chart
        tk.Label(self.out_inner, text="GANTT CHART",
                 font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=ACCENT).pack(anchor="w", padx=16, pady=(12, 4))

        # Gantt canvas dimensions
        BAR_H     = 38
        TICK_H    = 20
        CANVAS_H  = BAR_H + TICK_H + 10
        MIN_SEG_W = 52

        seg_widths = [max(MIN_SEG_W, (seg[2] - seg[1]) * 22) for seg in gantt]
        chart_w    = sum(seg_widths) + 8

        gantt_wrap = tk.Frame(self.out_inner, bg=PANEL)
        gantt_wrap.pack(fill="x", padx=16, pady=(0, 6))

        gc = tk.Canvas(gantt_wrap, bg=PANEL, height=CANVAS_H,
                       highlightthickness=1, highlightbackground=BORDER)
        h_sb = ttk.Scrollbar(gantt_wrap, orient="horizontal",
                              command=gc.xview)
        gc.configure(xscrollcommand=h_sb.set,
                     scrollregion=(0, 0, chart_w, CANVAS_H))
        h_sb.pack(side="bottom", fill="x")
        gc.pack(side="top", fill="x")

        # Draw each segment bar
        x = 4
        for i, seg in enumerate(gantt):
            pid, s, e = seg
            w   = seg_widths[i]
            col = IDLE_COL if pid == "IDLE" else pid_color[pid]

            gc.create_rectangle(x, 4, x + w, 4 + BAR_H,
                                 fill=col, outline=PANEL, width=2)
            txt_col = TEXT_DIM if pid == "IDLE" else TEXT
            gc.create_text(x + w // 2, 4 + BAR_H // 2,
                           text=pid, font=("Segoe UI", 8, "bold"),
                           fill=txt_col)
            # Tick mark at start
            tick_y = 4 + BAR_H
            gc.create_line(x, tick_y, x, tick_y + 5, fill=TEXT_DIM, width=1)
            gc.create_text(x + 2, tick_y + 13,
                           text=str(s), font=FONT_XS,
                           fill=TEXT_DIM, anchor="w")
            x += w

        # Final tick mark at end
        tick_y = 4 + BAR_H
        gc.create_line(x, tick_y, x, tick_y + 5, fill=TEXT_DIM, width=1)
        gc.create_text(x + 2, tick_y + 13,
                       text=str(gantt[-1][2]),
                       font=FONT_XS, fill=TEXT_DIM, anchor="w")

        # Color legend for process IDs
        leg = tk.Frame(self.out_inner, bg=PANEL)
        leg.pack(anchor="w", padx=16, pady=(2, 10))
        for pid, col in pid_color.items():
            dot = tk.Frame(leg, bg=col, width=11, height=11)
            dot.pack(side="left")
            dot.pack_propagate(False)
            tk.Label(leg, text=pid, font=FONT_XS,
                     bg=PANEL, fg=TEXT_MED).pack(side="left", padx=(3, 10))

        tk.Frame(self.out_inner, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 6))

        # ── Section label — Process Table
        tk.Label(self.out_inner, text="PROCESS TABLE",
                 font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=ACCENT).pack(anchor="w", padx=16, pady=(4, 6))

        has_pri = key in ("priority", "prr")
        cols    = ["PID", "Arrival", "Burst"]
        if has_pri:
            cols.append("Priority")
        cols += ["Completion", "Turnaround", "Waiting"]

        # Table rendered as a bordered grid using 1-px BORDER gaps
        tbl = tk.Frame(self.out_inner, bg=BORDER)
        tbl.pack(fill="x", padx=16, pady=(0, 12))
        for j in range(len(cols)):
            tbl.columnconfigure(j, weight=1)

        col_w = 9

        # Header row
        for j, c in enumerate(cols):
            cell = tk.Frame(tbl, bg=PANEL_ALT)
            cell.grid(row=0, column=j, padx=1, pady=1, sticky="nsew")
            tk.Label(cell, text=c,
                     font=FONT_XS,
                     bg=PANEL_ALT, fg=TEXT_MED,
                     width=col_w, anchor="center").pack(padx=6, pady=7)

        # Data rows — alternate PANEL / PANEL_ALT for readability
        for i, p in enumerate(procs):
            row_bg = PANEL if i % 2 == 0 else PANEL_ALT
            vals   = [p["pid"], p["at"], p["bt"]]
            if has_pri:
                vals.append(p["priority"])
            vals += [p["ct"], p["tat"], p["wt"]]
            for j, v in enumerate(vals):
                cell = tk.Frame(tbl, bg=row_bg)
                cell.grid(row=i + 1, column=j, padx=1, pady=1, sticky="nsew")
                tk.Label(cell, text=str(v),
                         font=FONT_MONO, bg=row_bg, fg=TEXT,
                         width=col_w, anchor="center").pack(padx=6, pady=6)

        tk.Frame(self.out_inner, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 6))

        # ── Summary stat cards — Average WT and Average TAT
        n       = len(procs)
        avg_wt  = sum(p["wt"]  for p in procs) / n
        avg_tat = sum(p["tat"] for p in procs) / n

        avg_row = tk.Frame(self.out_inner, bg=PANEL)
        avg_row.pack(fill="x", padx=16, pady=(4, 18))

        for label, val, fg in [
            ("Avg. Waiting Time",      avg_wt,  ACCENT),
            ("Avg. Turnaround Time",   avg_tat, "#6abf77"),
        ]:
            card = tk.Frame(avg_row, bg=PANEL_ALT,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(side="left", expand=True, fill="both", padx=(0, 8))
            tk.Label(card, text=label.upper(),
                     font=("Segoe UI", 8),
                     bg=PANEL_ALT, fg=TEXT_DIM).pack(pady=(12, 2))
            tk.Label(card, text=f"{val:.2f}",
                     font=("Segoe UI", 24, "bold"),
                     bg=PANEL_ALT, fg=fg).pack(pady=(0, 12))

        self.out_canvas.yview_moveto(0)


# SIMULATION POINT

if __name__ == "__main__":
    app = CPUSchedulerApp()
    app.mainloop()