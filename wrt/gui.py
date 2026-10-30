"""
Water Reach Task - control window.

Tabs
    1. Setup     connect the Tinkerforge rig and/or the Arduino dispenser,
                 enter animal / session, choose the data folder
    2. Session   pick the task, check parameters, START / STOP, live view
    3. Tools     manual tests (beep, LEDs, valve, lick sensor, dispenser
                 commands) and water calibration
"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from . import config as C
from . import params as PR
from . import theme as th
from .camera import Camera
from .dispenser import HAVE_SERIAL, Dispenser, list_ports_available
from .recorder import Recorder
from .tf_rig import HAVE_TINKERFORGE, TinkerforgeRig
from .tf_task import TFRecorder, TFTaskRunner
from .training import TrainingRunner

BG, CARD, BORDER = th.BG, th.CARD, th.BORDER
MUTED, ACCENT = th.MUTED, th.PRIMARY_DK
OK_C, BAD_C, WARN_C = th.HIT_C, th.DANGER, th.WARN

SESSION_TYPES = [
    ("TF_CUE", "Cue-reward task  (Tinkerforge rig: beep, blue/green LED, valve, lick sensor)", True),
    ("TRAINING", PR.SESSIONS["TRAINING"]["name"], True),
    ("FUS", PR.SESSIONS["FUS"]["name"], False),
    ("DROPPLET", PR.SESSIONS["DROPPLET"]["name"], False),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Water Reach Task  -  v{__version__}")
        self.geometry("1100x740")
        self.minsize(860, 560)

        self.cfg = C.load()
        self.folder_base = C.output_dir(self.cfg)
        self.calib_path = os.path.join(self.folder_base, "calibration.json")
        self.calib = self._load_calib()

        self.rig = None          # TinkerforgeRig
        self.disp = None         # Arduino Dispenser
        self.cam = None          # Camera shuttle
        self.rec = None
        self.runner = None
        self.q = queue.Queue()
        self.var = {}
        self._busy = False

        self.f = th.apply(self)
        self._build()
        self.after(50, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =================================================================
    # layout helpers
    # =================================================================
    def _card(self, parent, title=None):
        outer = th.card(parent, title, pad=15)
        inner = outer.inner
        for m in ("pack", "grid", "place"):
            setattr(inner, m, getattr(outer, m))
        return inner

    def _scroll(self, parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        cv = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        inner = ttk.Frame(cv)
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def wheel(e):
            try:
                cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        inner.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", wheel))
        inner.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        return inner

    def _build(self):
        self.status = tk.StringVar(value="Ready. Start in tab 1 (Setup).")
        head = tk.Frame(self, bg=CARD)
        head.pack(fill="x")
        tk.Frame(head, bg=th.PRIMARY, height=3).pack(fill="x")
        top = ttk.Frame(head, style="Head.TFrame", padding=(18, 11))
        top.pack(fill="x")
        ttk.Label(top, text="Water Reach Task", style="H1.TLabel").pack(side="left")
        ttk.Label(top, text=f"   fUS integrated  v{__version__}",
                  style="Muted.TLabel").pack(side="left")
        self.lbl_conn = ttk.Label(top, text="Not connected", style="Accent.TLabel",
                                  foreground=BAD_C)
        self.lbl_conn.pack(side="right")
        tk.Frame(head, bg=BORDER, height=1).pack(fill="x")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.t1, self.t2, self.t3 = (ttk.Frame(self.nb, padding=14) for _ in range(3))
        self.nb.add(self.t1, text="1. Setup")
        self.nb.add(self.t2, text="2. Session")
        self.nb.add(self.t3, text="3. Tools")
        self._tab_setup()
        self._tab_session()
        self._tab_tools()

        bar = ttk.Frame(self, padding=(14, 3, 14, 8))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status, style="Status.TLabel").pack(side="left")

    # =================================================================
    # TAB 1 - SETUP
    # =================================================================
    def _tab_setup(self):
        t = self._scroll(self.t1)

        # ---- Tinkerforge ----
        c = self._card(t, "A.  Tinkerforge rig  (ESP32 Brick over WiFi)")
        c.pack(fill="x", pady=(0, 12))
        ttk.Label(c, style="Help.TLabel", text=(
            "1) Switch on the 12 V supply.  2) Connect this PC to the ESP32 Brick's "
            "WiFi network.  3) Click CONNECT RIG.  With address 'auto' the brick is "
            "found automatically; the Bricklets are detected by type.")).pack(anchor="w", pady=(0, 10))
        g = ttk.Frame(c, style="Card.TFrame")
        g.pack(fill="x")
        ttk.Label(g, text="Address:", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        self.var_host = tk.StringVar(value=str(self.cfg["tinkerforge"].get("host", "auto")))
        ttk.Entry(g, textvariable=self.var_host, width=18).grid(row=0, column=1, padx=8, sticky="w")
        ttk.Label(g, text="Port:", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        self.var_tfport = tk.IntVar(value=int(self.cfg["tinkerforge"].get("port", 4223)))
        ttk.Entry(g, textvariable=self.var_tfport, width=7).grid(row=0, column=3, padx=8, sticky="w")
        self.btn_rig = ttk.Button(g, text="CONNECT RIG", style="Primary.TButton",
                                  command=self._connect_rig)
        self.btn_rig.grid(row=0, column=4, padx=(16, 6))
        self.btn_rig_off = ttk.Button(g, text="Disconnect", command=self._disconnect_rig,
                                      state="disabled")
        self.btn_rig_off.grid(row=0, column=5)
        self.lbl_rig = ttk.Label(c, style="Help.TLabel", text="Not connected.")
        self.lbl_rig.pack(anchor="w", pady=(10, 0))

        # ---- Arduino + camera ----
        c2 = self._card(t, "B.  Arduino droplet dispenser + camera shuttle  (USB serial, optional)")
        c2.pack(fill="x", pady=(0, 12))
        ttk.Label(c2, style="Help.TLabel", text=(
            "Needed only for the 'Arduino dispenser training' session. The camera "
            "shuttle can also be used together with the Tinkerforge task: each trial "
            "is then named, started and stopped on the camera.")).pack(anchor="w", pady=(0, 10))
        g2 = ttk.Frame(c2, style="Card.TFrame")
        g2.pack(fill="x")
        self.cmb_disp = ttk.Combobox(g2, width=42, state="readonly")
        self.cmb_cam = ttk.Combobox(g2, width=42, state="readonly")
        for i, (lab, cmb) in enumerate((("Dispenser (Arduino):", self.cmb_disp),
                                        ("Camera shuttle:", self.cmb_cam))):
            ttk.Label(g2, text=lab, style="Card.TLabel").grid(row=i, column=0, sticky="w", pady=4)
            cmb.grid(row=i, column=1, sticky="w", pady=4, padx=8)
        ttk.Button(g2, text="Scan ports", command=self._scan).grid(row=0, column=2, padx=8)
        b = ttk.Frame(c2, style="Card.TFrame")
        b.pack(anchor="w", pady=(10, 0))
        self.btn_ser = ttk.Button(b, text="Connect dispenser", command=self._connect_serial)
        self.btn_ser.pack(side="left")
        self.btn_cam = ttk.Button(b, text="Connect camera only", command=self._connect_camera)
        self.btn_cam.pack(side="left", padx=8)
        self.btn_ser_off = ttk.Button(b, text="Disconnect serial", command=self._disconnect_serial,
                                      state="disabled")
        self.btn_ser_off.pack(side="left")
        self.lbl_ser = ttk.Label(c2, style="Help.TLabel", text="Not connected.")
        self.lbl_ser.pack(anchor="w", pady=(8, 0))

        # ---- animal / session ----
        c3 = self._card(t, "C.  Animal and session")
        c3.pack(fill="x", pady=(0, 12))
        g3 = ttk.Frame(c3, style="Card.TFrame")
        g3.pack(fill="x")
        self.var_animal, self.var_session, self.var_note = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for i, (lab, v, w) in enumerate((("Animal ID (required):", self.var_animal, 24),
                                          ("Session ID:", self.var_session, 24),
                                          ("Note (optional):", self.var_note, 56))):
            ttk.Label(g3, text=lab, style="Card.TLabel").grid(row=i, column=0, sticky="w", pady=5)
            ttk.Entry(g3, textvariable=v, width=w).grid(row=i, column=1, sticky="w", pady=5, padx=8)

        # ---- data folder ----
        c4 = self._card(t, "D.  Data folder")
        c4.pack(fill="x")
        r = ttk.Frame(c4, style="Card.TFrame")
        r.pack(fill="x")
        self.var_dir = tk.StringVar(value=self.folder_base)
        ttk.Entry(r, textvariable=self.var_dir, width=64).pack(side="left")
        ttk.Button(r, text="Change", command=self._pick_dir).pack(side="left", padx=8)
        ttk.Button(r, text="Open folder", command=self._open_dir).pack(side="left")
        ttk.Label(c4, style="Help.TLabel", text=(
            "Every session creates its own sub-folder named "
            "<animal>_<session>_<date>_<time>. Data is saved after every trial.")
                  ).pack(anchor="w", pady=(8, 0))
        self._scan()

    # =================================================================
    # TAB 2 - SESSION
    # =================================================================
    def _tab_session(self):
        tab = self.t2
        bar = ttk.Frame(tab, padding=(0, 10, 0, 0))
        bar.pack(side="bottom", fill="x")
        ttk.Separator(tab).pack(side="bottom", fill="x")
        self.btn_start = ttk.Button(bar, text="START", style="Primary.TButton",
                                    command=self._start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(bar, text="STOP", style="Stop.TButton",
                                   command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=10)
        self.lbl_file = ttk.Label(bar, text="", style="Status.TLabel")
        self.lbl_file.pack(side="left", padx=12)

        t = self._scroll(tab)
        c0 = self._card(t, "Task")
        c0.pack(fill="x", pady=(0, 12))
        self.var_sess = tk.StringVar(value="TF_CUE")
        for sid, name, runnable in SESSION_TYPES:
            ttk.Radiobutton(c0, text=name, value=sid, variable=self.var_sess,
                            state="normal" if runnable else "disabled",
                            command=self._load_sess).pack(anchor="w", pady=2)
        ttk.Label(c0, style="Help.TLabel", text=(
            "fUS sessions drive the Verasonics scanner (SCAN.doppler) and must be "
            "run from MATLAB. Their parameters are listed in wrt/params.py.")
                  ).pack(anchor="w", pady=(6, 0))

        pc = self._card(t, "Parameters")
        pc.pack(fill="x", pady=(0, 12))
        self.card_v = ttk.Frame(pc, style="Card.TFrame")
        self.card_v.pack(fill="x")

        cst = self._card(t, "Live status")
        cst.pack(fill="x", pady=(0, 12))
        grid = ttk.Frame(cst, style="Card.TFrame")
        grid.pack(fill="x")
        self.sv = {}
        for i, (lab, key) in enumerate((("TRIAL", "trial"), ("CUE", "led"),
                                        ("LICKS THIS TRIAL", "licks"),
                                        ("TRIALS WITH LICKS", "hit"), ("RATE %", "rate"),
                                        ("TOTAL LICKS", "total"))):
            ttk.Label(grid, text=lab, style="StatLbl.TLabel").grid(row=0, column=i, padx=12, sticky="w")
            v = tk.StringVar(value="-")
            self.sv[key] = v
            ttk.Label(grid, textvariable=v, style="StatVal.TLabel").grid(row=1, column=i, padx=12, sticky="w")
        ttk.Separator(cst).pack(fill="x", pady=(12, 8))
        self.lbl_phase = ttk.Label(cst, text="Session not started", style="Card.TLabel",
                                   font=self.f.big)
        self.lbl_phase.pack(anchor="w")
        self.txt_log = tk.Text(cst, height=6, bg="#0e1a18", fg="#d7e8e4", relief="flat",
                               font=self.f.mono, padx=10, pady=8)
        self.txt_log.pack(fill="x", pady=(8, 0))

        cg = self._card(t, "Trial history  (tall bar = licked; colour = cue;  line = rate over last 20 trials)")
        cg.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cg, bg=CARD, height=180, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._load_sess()

    def _param_rows(self, items):
        card = self.card_v
        for w in card.winfo_children():
            w.destroy()
        self.var.clear()
        for key, label, typ, note in items:
            f = ttk.Frame(card, style="Card.TFrame")
            f.pack(fill="x", pady=3)
            ttk.Label(f, text=label, style="Card.TLabel", width=28).grid(row=0, column=0, sticky="w")
            v = tk.DoubleVar(value=self._val(key)) if typ is float else tk.IntVar(value=self._val(key))
            inc = 0.05 if typ is float else 1
            ttk.Spinbox(f, from_=0, to=100000, increment=inc, textvariable=v,
                        width=10).grid(row=0, column=1, sticky="w", padx=(0, 10))
            ttk.Label(f, text=note, style="Muted.TLabel").grid(row=0, column=2, sticky="w")
            self.var[key] = (v, typ)

    def _val(self, key):
        return self._defaults.get(key, 0)

    def _load_sess(self):
        sid = self.var_sess.get()
        if sid == "TF_CUE":
            self._defaults = dict(self.cfg["task"])
            self._param_rows(PR.TF_FIELDS)
            ttk.Label(self.card_v, style="Help.TLabel", text=(
                "Defaults come from config.json. Changes made here apply to this "
                "session only and are saved in the session files.")).pack(anchor="w", pady=(8, 0))
        else:
            s = PR.SESSIONS[sid]
            items, self._defaults = [], {}
            for group in ("vars", "params"):
                for k, info in s[group].items():
                    self._defaults[k] = info["value"]
                    typ = float if isinstance(info["value"], float) else int
                    items.append((k, k, typ, f"{info['source']}   {info.get('note', '')}"))
            self._param_rows(items)

    def _collect(self):
        out = {}
        for k, (v, typ) in self.var.items():
            try:
                out[k] = typ(v.get())
            except Exception:
                raise ValueError(f"Invalid value for '{k}'")
        return out

    # =================================================================
    # TAB 3 - TOOLS
    # =================================================================
    def _tab_tools(self):
        t = self._scroll(self.t3)

        c = self._card(t, "Tinkerforge rig - manual test")
        c.pack(fill="x", pady=(0, 12))
        ttk.Label(c, style="Help.TLabel", text=(
            "Use these buttons to check every part of the rig before an animal "
            "session. They are disabled while a session is running.")).pack(anchor="w", pady=(0, 10))
        g = ttk.Frame(c, style="Card.TFrame")
        g.pack(fill="x")
        self.tf_toggle = {"blue": False, "green": False}
        btns = (("Beep", self._tf_beep), ("Blue LED on/off", lambda: self._tf_led("blue")),
                ("Green LED on/off", lambda: self._tf_led("green")),
                ("Valve pulse", self._tf_pulse), ("All outputs OFF", self._tf_off))
        for i, (lab, fn) in enumerate(btns):
            ttk.Button(g, text=lab, command=fn).grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            g.columnconfigure(i, weight=1)
        r = ttk.Frame(c, style="Card.TFrame")
        r.pack(fill="x", pady=(10, 0))
        ttk.Label(r, text="Valve pulse (s):", style="Card.TLabel").pack(side="left")
        self.var_pulse = tk.DoubleVar(value=float(self.cfg["task"]["valve_duration_s"]))
        ttk.Spinbox(r, from_=0.01, to=10, increment=0.05, textvariable=self.var_pulse,
                    width=7).pack(side="left", padx=6)
        ttk.Label(r, text="   Pulses for calibration:", style="Card.TLabel").pack(side="left")
        self.var_npulse = tk.IntVar(value=50)
        ttk.Spinbox(r, from_=1, to=1000, textvariable=self.var_npulse, width=7).pack(side="left", padx=6)
        ttk.Button(r, text="Run N pulses", command=self._tf_npulse).pack(side="left", padx=6)
        lr = ttk.Frame(c, style="Card.TFrame")
        lr.pack(fill="x", pady=(12, 0))
        ttk.Label(lr, text="Lick sensor:", style="Card.TLabel").pack(side="left")
        self.lick_dot = tk.Canvas(lr, width=22, height=22, bg=CARD, highlightthickness=0)
        self.lick_dot.pack(side="left", padx=8)
        self._lick_oval = self.lick_dot.create_oval(3, 3, 19, 19, fill=th.FAINT, outline="")
        self.lbl_lick = ttk.Label(lr, text="(connect the rig to see live touches)", style="Muted.TLabel")
        self.lbl_lick.pack(side="left")
        self._lick_n = 0
        self._lick_last = False

        c2 = self._card(t, "Arduino dispenser - manual commands")
        c2.pack(fill="x", pady=(0, 12))
        g2 = ttk.Frame(c2, style="Card.TFrame")
        g2.pack(fill="x")
        for i, (lab, m) in enumerate((("Single drop (1)", "dropplet"), ("Sound (10)", "audio"),
                                      ("Sound + drop (11)", "audio_and_drop"),
                                      ("Sound, delay, drop (13)", "audio_delay_drop"),
                                      ("Reset clock (12)", "reset_time"))):
            ttk.Button(g2, text=lab, command=lambda m=m: self._cmd(m)).grid(
                row=i // 3, column=i % 3, padx=4, pady=4, sticky="ew")
        for col in range(3):
            g2.columnconfigure(col, weight=1)
        pf = ttk.Frame(c2, style="Card.TFrame")
        pf.pack(fill="x", pady=(10, 0))
        self.tool_par = {}
        for i, key in enumerate(("ParDropSize", "ParAudioDuration", "ParDelayAudioDrop")):
            ttk.Label(pf, text=key + " (ms)", style="Card.TLabel").grid(row=0, column=i * 2, sticky="w")
            v = tk.IntVar(value=PR.FIRMWARE_DEFAULTS[key])
            self.tool_par[key] = v
            ttk.Spinbox(pf, from_=0, to=32767, textvariable=v, width=8).grid(
                row=0, column=i * 2 + 1, padx=(4, 14))
        ttk.Button(pf, text="Write parameters", command=self._tool_write_params).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        fr = ttk.Frame(c2, style="Card.TFrame")
        fr.pack(fill="x", pady=(10, 0))
        ttk.Label(fr, text="Flush (2), ms:", style="Card.TLabel").pack(side="left")
        self.var_flush = tk.IntVar(value=PR.FLUSH_MS)
        ttk.Spinbox(fr, from_=1, to=10000, textvariable=self.var_flush, width=8).pack(side="left", padx=6)
        ttk.Button(fr, text="Send flush", command=lambda: self._cmd("flush", self.var_flush.get())
                   ).pack(side="left", padx=6)
        self.txt_ev = tk.Text(c2, height=6, bg="#0e1a18", fg="#d7e8e4", relief="flat",
                              font=self.f.mono, padx=10, pady=8)
        self.txt_ev.pack(fill="x", pady=(10, 0))
        ttk.Label(c2, style="Muted.TLabel", text="Raw dispenser events (shown when no session is running)"
                  ).pack(anchor="w")

        c3 = self._card(t, "Water calibration  (how many microlitres per reward?)")
        c3.pack(fill="x")
        ttk.Label(c3, style="Help.TLabel", text=(
            "Place a tared cup on a balance under the spout, deliver N rewards "
            "(Tinkerforge: 'Run N pulses'; Arduino: 'Deliver drops'), weigh, and "
            "enter the weight. 1 mg of water = 1 uL.")).pack(anchor="w", pady=(0, 10))
        g3 = ttk.Frame(c3, style="Card.TFrame")
        g3.pack(fill="x")
        self.cal_dev = tk.StringVar(value="Tinkerforge valve")
        ttk.Combobox(g3, textvariable=self.cal_dev, state="readonly", width=20,
                     values=("Tinkerforge valve", "Arduino dispenser")).grid(row=0, column=0, padx=(0, 12))
        self.cal_set = tk.DoubleVar(value=float(self.cfg["task"]["valve_duration_s"]))
        self.cal_n = tk.IntVar(value=50)
        self.cal_mg = tk.DoubleVar(value=0.0)
        for i, (lab, v) in enumerate((("Setting (s or ms):", self.cal_set),
                                      ("Count:", self.cal_n), ("Weight (mg):", self.cal_mg))):
            ttk.Label(g3, text=lab, style="Card.TLabel").grid(row=0, column=1 + i * 2, sticky="w")
            ttk.Entry(g3, textvariable=v, width=9).grid(row=0, column=2 + i * 2, padx=(4, 12))
        b3 = ttk.Frame(c3, style="Card.TFrame")
        b3.pack(fill="x", pady=(10, 0))
        ttk.Button(b3, text="Deliver drops (Arduino)", command=self._cal_run).pack(side="left")
        ttk.Button(b3, text="Save measurement", command=self._cal_save).pack(side="left", padx=8)
        self.lbl_cal = ttk.Label(b3, text="", style="Accent.TLabel")
        self.lbl_cal.pack(side="left", padx=10)
        cols = ("device", "setting", "count", "mg", "uL_per_reward")
        self.cal_tree = ttk.Treeview(c3, columns=cols, show="headings", height=5)
        for cc, w in zip(cols, (150, 90, 70, 80, 120)):
            self.cal_tree.heading(cc, text=cc)
            self.cal_tree.column(cc, width=w, anchor="center")
        self.cal_tree.pack(fill="x", pady=(10, 0))
        self._cal_refresh()

    # =================================================================
    # connections
    # =================================================================
    def _connect_rig(self):
        if not HAVE_TINKERFORGE:
            messagebox.showerror("Missing package", "Run:  pip install -r requirements.txt")
            return
        if self._busy:
            return
        self._busy = True
        self.btn_rig.configure(state="disabled")
        self.lbl_rig.configure(text="Searching for the rig ...")
        tf = dict(self.cfg["tinkerforge"])
        tf["host"] = self.var_host.get().strip() or "auto"
        try:
            tf["port"] = int(self.var_tfport.get())
        except Exception:
            tf["port"] = 4223

        def work():
            try:
                rig = TinkerforgeRig(tf, self.cfg["relay_channels"])
                rig.connect(log=lambda m: self.q.put(("rig_msg", m)))
                self.q.put(("rig_ok", rig))
            except Exception as e:
                self.q.put(("rig_fail", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _disconnect_rig(self):
        if self.runner and isinstance(self.runner, TFTaskRunner):
            self._stop()
        if self.rig:
            self.rig.close()
        self.rig = None
        self.btn_rig.configure(state="normal")
        self.btn_rig_off.configure(state="disabled")
        self.lbl_rig.configure(text="Not connected.")
        self._update_conn_label()

    def _scan(self):
        ports = list_ports_available()
        labels = [p[1] for p in ports]
        self._pmap = {p[1]: p[0] for p in ports}
        for cmb, want in ((self.cmb_disp, self.cfg["serial"].get("dispenser_port", "")),
                          (self.cmb_cam, self.cfg["serial"].get("camera_port", ""))):
            cmb["values"] = labels
            hit = [l for l in labels if want and l.startswith(want + " ")]
            if hit:
                cmb.set(hit[0])
            elif labels:
                cmb.current(0)
        if not HAVE_SERIAL:
            self.status.set("pyserial not installed: pip install -r requirements.txt")

    def _connect_serial(self):
        dp = self._pmap.get(self.cmb_disp.get())
        if not dp:
            messagebox.showwarning("Port", "Select the dispenser port first.")
            return
        try:
            self.disp = Dispenser(dp)
            self.disp.open()
        except Exception as e:
            self.disp = None
            messagebox.showerror("Dispenser not connected", str(e))
            return
        cp = self._pmap.get(self.cmb_cam.get())
        if cp and cp != dp and self.cam is None:
            if messagebox.askyesno("Camera", f"Also connect the camera shuttle on {cp}?"):
                self._open_camera(cp)
        self.cfg["serial"]["dispenser_port"] = dp
        self._serial_done()

    def _connect_camera(self):
        cp = self._pmap.get(self.cmb_cam.get())
        if not cp:
            messagebox.showwarning("Port", "Select the camera port first.")
            return
        if self._open_camera(cp):
            self._serial_done()

    def _open_camera(self, cp):
        try:
            self.cam = Camera(cp, timeout=3)
            self.cam.open()
            self.cfg["serial"]["camera_port"] = cp
            return True
        except Exception as e:
            self.cam = None
            messagebox.showwarning("Camera not connected", str(e))
            return False

    def _serial_done(self):
        parts = []
        if self.disp:
            parts.append(f"dispenser on {self.disp.port}")
        if self.cam:
            parts.append(f"camera on {self.cam.port}")
        self.lbl_ser.configure(text="Connected: " + ", ".join(parts) if parts else "Not connected.")
        self.btn_ser_off.configure(state="normal" if parts else "disabled")
        self._save_cfg()
        self._update_conn_label()

    def _disconnect_serial(self):
        if self.runner and isinstance(self.runner, TrainingRunner):
            self._stop()
        for d in (self.disp, self.cam):
            try:
                if d:
                    d.close()
            except Exception:
                pass
        self.disp = self.cam = None
        self._serial_done()

    def _update_conn_label(self):
        parts = []
        if self.rig:
            parts.append("Rig")
        if self.disp:
            parts.append("Dispenser")
        if self.cam:
            parts.append("Camera")
        self.lbl_conn.configure(text=("Connected: " + " + ".join(parts)) if parts else "Not connected",
                                foreground=OK_C if parts else BAD_C)

    def _save_cfg(self):
        try:
            C.save(self.cfg)
        except Exception:
            pass

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_dir.get())
        if d:
            self.var_dir.set(d)
            self.folder_base = d
            self.cfg["output_dir"] = d
            self._save_cfg()
            self.calib_path = os.path.join(d, "calibration.json")
            self.calib = self._load_calib()
            self._cal_refresh()

    def _open_dir(self):
        d = self.var_dir.get()
        os.makedirs(d, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(d)
            else:
                os.system(f'xdg-open "{d}" 2>/dev/null')
        except Exception:
            messagebox.showinfo("Folder", d)

    # =================================================================
    # session control
    # =================================================================
    def _start(self):
        if self.runner:
            return
        sid = self.var_sess.get()
        if not self.var_animal.get().strip():
            messagebox.showwarning("Missing information", "Enter the animal ID in tab 1 (Setup).")
            self.nb.select(self.t1)
            return
        try:
            vals = self._collect()
        except ValueError as e:
            messagebox.showerror("Parameters", str(e))
            return
        emit = lambda kind, payload: self.q.put((kind, payload))
        folder = self.var_dir.get()
        os.makedirs(folder, exist_ok=True)

        if sid == "TF_CUE":
            if not self.rig:
                messagebox.showwarning("Rig not connected", "Connect the Tinkerforge rig in tab 1 first.")
                self.nb.select(self.t1)
                return
            params = dict(self.cfg["task"])
            params.update(vals)
            self.rec = TFRecorder(folder, self.var_animal.get(), self.var_session.get(),
                                  self.var_note.get(), params)
            self.runner = TFTaskRunner(self.rig, self.rec, emit, params, camera=self.cam)
        elif sid == "TRAINING":
            if not self.disp:
                messagebox.showwarning("Dispenser not connected",
                                       "Connect the Arduino dispenser in tab 1 first.")
                self.nb.select(self.t1)
                return
            self.rec = Recorder(folder, self.var_animal.get(), self.var_session.get(),
                                "TRAINING", self.var_note.get())
            self.runner = TrainingRunner(self.disp, self.cam, self.rec, emit, overrides=vals)
        else:
            messagebox.showinfo("MATLAB required", "This session must be run from MATLAB.")
            return

        self._sid_running = sid
        self.txt_log.delete("1.0", "end")
        self.canvas.delete("all")
        for v in self.sv.values():
            v.set("-")
        self.runner.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_file.configure(text=f"Saving to: {self.rec.sub_folder}")
        self.status.set("Session running. Press STOP to end early (data is kept).")

    def _stop(self):
        if self.runner:
            self.lbl_phase.configure(text="Stopping ...", foreground=MUTED)
            self.runner.stop()

    def _finish(self, completed_all):
        runner, self.runner = self.runner, None
        if runner:
            runner.join(3.0)
        rec = self.rec
        if rec and not rec.closed:
            if isinstance(rec, TFRecorder):
                rec.close(completed_all=completed_all)
                st = rec.stats()
                msg = (f"Trials completed: {st['all']['trials']}\n"
                       f"Trials with licks: {st['all']['licked']}  ({st['all']['rate']*100:.0f}%)\n"
                       f"  BLUE:  {st['BLUE']['licked']}/{st['BLUE']['trials']}\n"
                       f"  GREEN: {st['GREEN']['licked']}/{st['GREEN']['trials']}\n"
                       f"Total licks: {st['all']['licks']}\n\nFolder:\n{rec.folder}")
            else:
                rec.close(getattr(runner, "v", None), getattr(runner, "p", None), completed_all)
                st = rec.stats()
                msg = (f"Trials completed: {st['trials']}\n"
                       f"Trials with touch after drop: {st['with_touch']}  ({st['rate']*100:.0f}%)\n"
                       f"Median latency: {st['median_latency_ms']} ms\n"
                       f"Total touches: {st['total_touch']}\n\nFolder:\n{rec.folder}")
            messagebox.showinfo("Session finished" if completed_all else "Session stopped", msg)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_phase.configure(text="Session finished" if completed_all else "Session stopped",
                                 foreground=MUTED)
        self.status.set("Ready.")

    # =================================================================
    # tools - Tinkerforge
    # =================================================================
    def _tf_ready(self):
        if not self.rig:
            messagebox.showwarning("Rig not connected", "Connect the Tinkerforge rig first (tab 1).")
            return False
        if self.runner:
            messagebox.showwarning("Session running", "Manual controls are disabled during a session.")
            return False
        return True

    def _tf_async(self, fn, done_text):
        def work():
            try:
                fn()
                self.q.put(("status", done_text))
            except Exception as e:
                self.q.put(("error", {"message": str(e)}))
        threading.Thread(target=work, daemon=True).start()

    def _tf_beep(self):
        if self._tf_ready():
            p = self.cfg["task"]
            self._tf_async(lambda: self.rig.beep(p["beep_frequency_hz"], p["beep_volume"],
                                                 p["beep_duration_ms"]), "Beep sent.")

    def _tf_led(self, which):
        if self._tf_ready():
            self.tf_toggle[which] = not self.tf_toggle[which]
            on = self.tf_toggle[which]
            kw = {"blue": on} if which == "blue" else {"green": on}
            self._tf_async(lambda: self.rig.set_outputs(**kw),
                           f"{which.capitalize()} LED {'ON' if on else 'OFF'}.")

    def _tf_pulse(self):
        if self._tf_ready():
            s = float(self.var_pulse.get())
            self._tf_async(lambda: self.rig.valve_pulse(s), f"Valve pulse {s:.3f} s done.")

    def _tf_npulse(self):
        if self._tf_ready():
            s, n = float(self.var_pulse.get()), int(self.var_npulse.get())

            def run():
                for _ in range(n):
                    self.rig.valve_pulse(s)
                    time.sleep(0.3)
            self.cal_dev.set("Tinkerforge valve")
            self.cal_set.set(s)
            self.cal_n.set(n)
            self._tf_async(run, f"{n} valve pulses of {s:.3f} s done - now weigh the water.")

    def _tf_off(self):
        if self.rig:
            self.tf_toggle = {"blue": False, "green": False}
            self._tf_async(self.rig.all_off, "All rig outputs OFF.")

    # =================================================================
    # tools - Arduino
    # =================================================================
    def _cmd(self, method, *a):
        if not self.disp:
            messagebox.showwarning("Not connected", "Connect the Arduino dispenser first (tab 1).")
            return
        try:
            getattr(self.disp, method)(*a)
            self.status.set(f"Sent: {method}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _tool_write_params(self):
        if not self.disp:
            messagebox.showwarning("Not connected", "Connect the Arduino dispenser first (tab 1).")
            return
        try:
            for k, v in self.tool_par.items():
                self.disp.set_param(k, int(v.get()))
            self.status.set("Dispenser parameters written.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =================================================================
    # calibration
    # =================================================================
    def _load_calib(self):
        try:
            with open(self.calib_path, encoding="utf-8") as f:
                return json.load(f).get("points", [])
        except Exception:
            return []

    def _cal_run(self):
        if not self.disp:
            messagebox.showwarning("Not connected", "Connect the Arduino dispenser first (tab 1).")
            return
        ms, n = int(self.cal_set.get()), int(self.cal_n.get())
        self.cal_dev.set("Arduino dispenser")
        disp = self.disp

        def run():
            disp.set_param("ParDropSize", ms)
            for _ in range(n):
                disp.dropplet()
                time.sleep(ms / 1000.0 + 0.25)
        self._tf_async(run, f"{n} drops delivered - now weigh the water.")

    def _cal_save(self):
        try:
            dev, setting = self.cal_dev.get(), float(self.cal_set.get())
            n, mg = int(self.cal_n.get()), float(self.cal_mg.get())
            if n <= 0:
                raise ValueError("Count must be greater than 0.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        ul = mg / n
        self.calib = [p for p in self.calib if not (p["device"] == dev and p["setting"] == setting)]
        self.calib.append({"device": dev, "setting": setting, "count": n, "mg": mg,
                           "ul_per_reward": ul})
        self.calib.sort(key=lambda p: (p["device"], p["setting"]))
        with open(self.calib_path, "w", encoding="utf-8") as f:
            json.dump({"points": self.calib}, f, indent=2)
        self._cal_refresh()
        self.lbl_cal.configure(text=f"Saved: {ul:.2f} uL per reward")

    def _cal_refresh(self):
        self.cal_tree.delete(*self.cal_tree.get_children())
        for p in self.calib:
            try:
                self.cal_tree.insert("", "end", values=(p["device"], p["setting"], p["count"],
                                                        f"{p['mg']:.1f}", f"{p['ul_per_reward']:.2f}"))
            except KeyError:
                pass

    # =================================================================
    # event pump (GUI thread)
    # =================================================================
    def _pump(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                self._handle(kind, payload)
        except queue.Empty:
            pass
        except Exception as e:
            self.status.set(f"Error: {e}")

        if not self.runner:
            # live lick indicator
            if self.rig and not self._busy and self.nb.index("current") == 2:
                touching = self.rig.read_lick()
                if touching and not self._lick_last:
                    self._lick_n += 1
                self._lick_last = touching
                self.lick_dot.itemconfigure(self._lick_oval, fill=OK_C if touching else th.FAINT)
                self.lbl_lick.configure(text=f"{'TOUCH' if touching else 'no touch'}   "
                                             f"(touches counted: {self._lick_n})")
            # raw dispenser events
            if self.disp:
                try:
                    for e in self.disp.get_events():
                        self.txt_ev.insert("end", f"{e['ms']:>8} ms  {e['code']:>3}  {e['label']}\n")
                        self.txt_ev.see("end")
                except Exception:
                    pass
        self._pid = self.after(100, self._pump)

    def _log(self, text):
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        if int(self.txt_log.index("end-1c").split(".")[0]) > 400:
            self.txt_log.delete("1.0", "100.0")

    def _handle(self, kind, p):
        if kind == "rig_msg":
            self.lbl_rig.configure(text=p)
        elif kind == "rig_ok":
            self.rig = p
            self._busy = False
            self.lbl_rig.configure(text="Connected.  " + "   |   ".join(p.device_summary()))
            self.btn_rig_off.configure(state="normal")
            self.cfg["tinkerforge"]["port"] = p.port
            self._save_cfg()
            self._update_conn_label()
            self.status.set("Rig connected. Go to tab 2 (Session) or test it in tab 3 (Tools).")
        elif kind == "rig_fail":
            self._busy = False
            self.btn_rig.configure(state="normal")
            self.lbl_rig.configure(text="Not connected.")
            messagebox.showerror("Rig not found", p)
        elif kind == "status":
            self.status.set(p)
        elif kind == "log":
            self._log(p["text"])
        elif kind == "trial_start":
            self.sv["trial"].set(f"{p['trial']}/{p['ntrials']}")
            self.sv["led"].set(p.get("led", "-"))
            self.sv["licks"].set("0")
            self.lbl_phase.configure(text=f"Trial {p['trial']} started", foreground=ACCENT)
        elif kind == "phase":
            self.lbl_phase.configure(text=p["text"], foreground=OK_C)
        elif kind == "wait_tick":
            self.lbl_phase.configure(text=f"Waiting without touch: {p['elapsed']:.1f} / "
                                          f"{p['need']} s   (resets: {p['resets']})",
                                     foreground=WARN_C)
        elif kind == "image":
            self.sv["led"].set(f"img {p['image']}/{p['nimag']}")
        elif kind == "lick":
            self.sv["licks"].set(str(p["count"]))
        elif kind == "trial_end":
            self._refresh_stats()
            self._draw()
        elif kind == "trial_aborted":
            self._log(f"Trial {p['trial']} aborted (not saved).")
        elif kind == "error":
            messagebox.showerror("Error", p.get("message", ""))
        elif kind == "finished":
            self._finish(p.get("completed_all", False))

    def _refresh_stats(self):
        if not self.rec:
            return
        st = self.rec.stats()
        if isinstance(self.rec, TFRecorder):
            a = st["all"]
            self.sv["hit"].set(str(a["licked"]))
            self.sv["rate"].set(f"{a['rate']*100:.0f}")
            self.sv["total"].set(str(a["licks"]))
        else:
            self.sv["hit"].set(str(st["with_touch"]))
            self.sv["rate"].set(f"{st['rate']*100:.0f}")
            self.sv["total"].set(str(st["total_touch"]))

    def _draw(self):
        c = self.canvas
        c.delete("all")
        if not self.rec:
            return
        outs = self.rec.outcomes()
        if not outs:
            return
        W, H = c.winfo_width() or 600, c.winfo_height() or 180
        L, R, T, B = 44, 14, 14, 30
        pw, ph = max(10, W - L - R), max(10, H - T - B)
        bw = max(2.0, min(14.0, pw / max(len(outs), 1)))
        for frac, lab in ((1.0, "100%"), (0.5, "50%"), (0.0, "0%")):
            yy = T + ph - frac * ph
            c.create_line(L, yy, W - R, yy, fill=th.PRIMARY_LT if frac == 0.5 else BORDER)
            c.create_text(L - 7, yy, text=lab, anchor="e", fill=MUTED, font=self.f.tiny)
        yb = T + ph + 7
        for i, (ok, col) in enumerate(outs):
            x = L + i * bw
            c.create_rectangle(x, yb, x + max(1.5, bw - 1), yb + (15 if ok else 6),
                               fill=col, outline="")
        buf, rate = [], []
        for ok, _ in outs:
            buf.append(1 if ok else 0)
            buf = buf[-20:]
            rate.append(sum(buf) / len(buf))
        if len(rate) > 1:
            step = pw / max(len(rate) - 1, 1)
            pts = []
            for i, v in enumerate(rate):
                pts += [L + i * step, T + ph - v * ph]
            c.create_line(*pts, fill=th.PRIMARY_DK, width=2, smooth=True)
        c.create_text(W - R, T - 4, text=f"{len(outs)} trials", anchor="e", fill=MUTED,
                      font=self.f.small)

    def _on_close(self):
        if self.runner and not messagebox.askyesno(
                "Session running", "A session is running. Stop it and quit?"):
            return
        try:
            if getattr(self, "_pid", None):
                self.after_cancel(self._pid)
            if self.runner:
                self.runner.stop()
                self.runner.join(3.0)
            if self.rec and not self.rec.closed:
                self.rec.close()
            if self.rig:
                self.rig.close()
            for d in (self.disp, self.cam):
                if d:
                    d.close()
        except Exception:
            pass
        self.destroy()


def main():
    App().mainloop()
