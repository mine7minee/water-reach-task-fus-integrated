"""
Cue-reward task on the Tinkerforge rig.

Timeline of ONE trial (default values, all editable in config.json / GUI):

    0.0 s   beep (1000 Hz, 500 ms)
    3.0 s   cue LED on  - BLUE or GREEN, chosen at random every trial
    6.0 s   valve opens for 0.3 s  (water reward), LED stays on
    9.0 s   LED off
   15.0 s   trial ends -> 0.5 s inter-trial interval -> next trial

The lick sensor is polled during the whole trial. Every lick (touch onset)
is counted and time-stamped relative to trial start.

Optional: if the camera shuttle (serial) is connected, each trial is also
named, started and stopped on the camera, like exp_Training.m does.
"""
import csv
import json
import os
import random
import threading
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .recorder import safe

BLUE, GREEN = "BLUE", "GREEN"


# ======================================================================
# Recorder - one folder per session
# ======================================================================
class TFRecorder:
    """Writes, inside <output>/<animal>_<session>_<date>_<time>/ :
        session.xlsx  - sheets 'Trial Data', 'Summary', 'Log'
        licks.csv     - one row per lick (trial, LED, time in trial)
        session.json  - parameters + summary (machine readable)
    The Excel file is saved after EVERY trial, so a crash loses nothing."""

    HEAD = ["Trial", "LED", "Licked", "Lick Count", "First Lick (s)",
            "Licks Before LED", "Licks LED On", "Licks After LED",
            "Trial Duration (s)", "Log"]

    def __init__(self, folder_base, animal, session, note, params):
        self.animal, self.session, self.note = safe(animal), safe(session or "S1"), note
        self.params = dict(params)
        self.started = datetime.now()
        self.sub_folder = (f"{self.animal}_{self.session}_"
                           f"{self.started.strftime('%Y%m%d_%H%M%S')}")
        self.folder = os.path.join(folder_base, self.sub_folder)
        os.makedirs(self.folder, exist_ok=True)
        self.xlsx = os.path.join(self.folder, "session.xlsx")
        self.trials = []
        self.closed = False

        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Trial Data"
        self.ws.append(self.HEAD)
        for c in range(1, len(self.HEAD) + 1):
            cell = self.ws.cell(row=1, column=c)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="2E75B6")
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
        for col, w in zip("ABCDEFGHIJ", (7, 8, 8, 11, 13, 13, 12, 13, 15, 70)):
            self.ws.column_dimensions[col].width = w
        self.ws.freeze_panes = "A2"
        self.ws_sum = self.wb.create_sheet("Summary")
        self.ws_log = self.wb.create_sheet("Log")
        self.ws_log.append(["Clock Time", "Trial", "Event"])
        for c in (1, 2, 3):
            self.ws_log.cell(row=1, column=c).font = Font(bold=True)
        self.ws_log.column_dimensions["A"].width = 13
        self.ws_log.column_dimensions["C"].width = 70
        self._save()

        self.csv_path = os.path.join(self.folder, "licks.csv")
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["trial", "led", "lick_number", "time_in_trial_s"])

    def _save(self):
        try:
            self.wb.save(self.xlsx)
        except PermissionError:
            # file open in Excel - save a side copy instead of crashing
            self.wb.save(self.xlsx.replace(".xlsx", "_autosave.xlsx"))

    def log(self, trial, text):
        self.ws_log.append([datetime.now().strftime("%H:%M:%S.%f")[:-3], trial, text])

    def write_trial(self, t):
        p = self.params
        led_on, led_off = p["led_start_s"], p["led_start_s"] + p["led_duration_s"]
        times = t["lick_times"]
        before = sum(1 for x in times if x < led_on)
        during = sum(1 for x in times if led_on <= x < led_off)
        after = sum(1 for x in times if x >= led_off)
        first = round(times[0], 2) if times else None
        row = [t["trial"], t["led"], 1 if times else 0, len(times), first,
               before, during, after, round(t["duration"], 2), "\n".join(t["log"])]
        self.ws.append(row)
        r = self.ws.max_row
        fill = PatternFill("solid", fgColor="BDD7EE" if t["led"] == BLUE else "E2EFDA")
        for c in range(1, 10):
            self.ws.cell(row=r, column=c).fill = fill
            self.ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
        self.ws.cell(row=r, column=10).alignment = Alignment(wrap_text=True, vertical="top")
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for i, x in enumerate(times, 1):
                w.writerow([t["trial"], t["led"], i, f"{x:.3f}"])
        t2 = dict(t, licked=bool(times), first_lick_s=first,
                  licks_before_led=before, licks_led_on=during, licks_after_led=after)
        self.trials.append(t2)
        self._save()
        return t2

    # ---- statistics ----
    def stats(self):
        def block(rows):
            n = len(rows)
            k = sum(1 for r in rows if r["licked"])
            return {"trials": n, "licked": k, "rate": (k / n) if n else 0.0,
                    "licks": sum(len(r["lick_times"]) for r in rows)}
        return {"all": block(self.trials),
                BLUE: block([r for r in self.trials if r["led"] == BLUE]),
                GREEN: block([r for r in self.trials if r["led"] == GREEN])}

    def outcomes(self):
        """For the live plot: list of (success, colour)."""
        return [(r["licked"], "#2f6db5" if r["led"] == BLUE else "#2f9e78")
                for r in self.trials]

    def close(self, completed_all=False):
        if self.closed:
            return
        st = self.stats()
        ws = self.ws_sum
        ws.append(["EXPERIMENT SUMMARY"])
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([])
        rows = [
            ["Animal", self.animal], ["Session", self.session], ["Note", self.note],
            ["Started", self.started.strftime("%Y-%m-%d %H:%M:%S")],
            ["Finished", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Completed Trials", f"{st['all']['trials']}/{self.params['total_trials']}"],
            ["Stopped Early", "No" if completed_all else "Yes"],
            [],
            ["ALL TRIALS", ""],
            ["Trials With Licks", f"{st['all']['licked']}/{st['all']['trials']} ({st['all']['rate']*100:.1f}%)"],
            ["Total Licks", st["all"]["licks"]],
            [],
            ["BLUE LED", ""],
            ["Blue Trials", st[BLUE]["trials"]],
            ["Blue Trials With Licks", f"{st[BLUE]['licked']}/{st[BLUE]['trials']} ({st[BLUE]['rate']*100:.1f}%)"],
            ["Blue Licks", st[BLUE]["licks"]],
            [],
            ["GREEN LED", ""],
            ["Green Trials", st[GREEN]["trials"]],
            ["Green Trials With Licks", f"{st[GREEN]['licked']}/{st[GREEN]['trials']} ({st[GREEN]['rate']*100:.1f}%)"],
            ["Green Licks", st[GREEN]["licks"]],
            [],
            ["PARAMETERS", ""],
        ] + [[k, v] for k, v in self.params.items()]
        for r in rows:
            ws.append(r)
            if len(r) == 2 and r[1] == "":
                ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 34
        self._save()
        meta = {"animal": self.animal, "session": self.session, "note": self.note,
                "task": "Tinkerforge cue-reward task",
                "started": self.started.isoformat(timespec="seconds"),
                "finished": datetime.now().isoformat(timespec="seconds"),
                "completed_all_trials": completed_all,
                "parameters": self.params, "summary": st, "trials": self.trials}
        with open(os.path.join(self.folder, "session.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        self.closed = True


# ======================================================================
# Runner - background thread, reports through emit(kind, payload)
# ======================================================================
class TFTaskRunner:
    def __init__(self, rig, recorder, emit, params, camera=None):
        self.rig, self.rec, self.emit = rig, recorder, emit
        self.p = dict(params)
        self.cam = camera
        self.stop_event = threading.Event()
        self._thread = None
        self.completed_all = False

    def start(self):
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.stop_event.set()

    def join(self, t=5.0):
        if self._thread:
            self._thread.join(timeout=t)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        try:
            self._loop()
        except Exception as e:
            self.emit("error", {"message": str(e)})
        finally:
            try:
                self.rig.all_off()
            except Exception:
                pass
            if self.cam is not None and getattr(self.cam, "connected", False):
                try:
                    self.cam.stop()
                except Exception:
                    pass
            self.emit("finished", {"completed_all": self.completed_all})

    # ------------------------------------------------------------------
    def _loop(self):
        p = self.p
        self.rig.configure_touch(p.get("lick_electrode", 0))
        if self.cam is not None and self.cam.connected:
            self.cam.mkdir(self.rec.sub_folder)
        n = int(p["total_trials"])
        for i in range(1, n + 1):
            if self.stop_event.is_set():
                return
            self._trial(i, n)
            if self.stop_event.is_set():
                return
            if i < n:
                self._sleep(p["inter_trial_interval_s"])
        self.completed_all = True

    def _sleep(self, sec):
        end = time.time() + float(sec)
        while time.time() < end and not self.stop_event.is_set():
            time.sleep(0.01)

    def _trial(self, i, n):
        p = self.p
        led = random.choice([BLUE, GREEN])
        log_lines = []
        licks = []
        t0 = time.time()
        last = [False]

        def log(msg):
            line = f"[{time.time() - t0:5.2f}s] {msg}"
            log_lines.append(line)
            self.rec.log(i, line)
            self.emit("log", {"text": f"Trial {i}: {line}"})

        def watch_until(t_rel):
            """Poll the lick sensor until t_rel seconds after trial start."""
            poll = float(p["lick_poll_interval_s"])
            while not self.stop_event.is_set():
                now = time.time() - t0
                if now >= t_rel:
                    break
                touching = self.rig.read_lick()
                if touching and not last[0]:
                    licks.append(now)
                    log(f"LICK #{len(licks)}")
                    self.emit("lick", {"trial": i, "count": len(licks), "t": now})
                last[0] = touching
                time.sleep(poll)

        def led_on(on):
            if led == BLUE:
                self.rig.set_outputs(blue=on)
            else:
                self.rig.set_outputs(green=on)

        if self.cam is not None and self.cam.connected:
            self.cam.set_name(f"CAM_{i:02d}")
            self.cam.set_idn(f"{i:02d}")
            self.cam.start()

        self.emit("trial_start", {"trial": i, "ntrials": n, "led": led})

        # 0 s - beep
        self.rig.beep(p["beep_frequency_hz"], p["beep_volume"], p["beep_duration_ms"])
        log(f"Beep ({p['beep_frequency_hz']} Hz, {p['beep_duration_ms']} ms)")

        # build the event schedule (works for any timing values)
        led_start = float(p["led_start_s"])
        led_end = led_start + float(p["led_duration_s"])
        v_open = float(p["valve_time_s"])
        v_close = v_open + float(p["valve_duration_s"])
        events = sorted([
            (led_start, 0, "led_on"), (led_end, 1, "led_off"),
            (v_open, 2, "valve_open"), (v_close, 3, "valve_close")])
        for t_ev, _, kind in events:
            watch_until(t_ev)
            if self.stop_event.is_set():
                break
            if kind == "led_on":
                led_on(True); log(f"{led} LED on")
                self.emit("phase", {"text": f"{led} LED on"})
            elif kind == "led_off":
                led_on(False); log(f"{led} LED off")
                self.emit("phase", {"text": "LED off"})
            elif kind == "valve_open":
                self.rig.set_outputs(valve=True)
                log(f"Valve open ({int(p['valve_duration_s'] * 1000)} ms)")
                self.emit("phase", {"text": "REWARD - valve open"})
            elif kind == "valve_close":
                self.rig.set_outputs(valve=False); log("Valve closed")

        watch_until(float(p["trial_duration_s"]))
        self.rig.all_off()
        if self.cam is not None and self.cam.connected:
            self.cam.stop()

        dur = time.time() - t0
        if self.stop_event.is_set():
            log("Trial aborted by user - not saved")
            self.emit("trial_aborted", {"trial": i})
            return
        log(f"Trial done | licked: {'YES' if licks else 'NO'} | licks: {len(licks)}")
        row = self.rec.write_trial({"trial": i, "led": led, "lick_times": licks,
                                    "duration": dur, "log": log_lines})
        self.emit("trial_end", {"trial": i, "row": row})
