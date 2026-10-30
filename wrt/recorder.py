"""
Data recording for the Arduino dispenser training session
(equivalent of save() and the folder layout in exp_Training.m).

Folder:  <output>/<animal>_<session>_<YYYYmmdd_HHMMSS>/
    FUS_01.json ...  mdExt + Events + EventsBefore (same content as the MATLAB .mat)
    events.csv       all events of the session in one table
    session.json     parameters, sources and summary

Read a trial file in MATLAB with:  jsondecode(fileread('FUS_01.json'))
"""
import csv
import json
import os
from datetime import datetime

from . import params as PR


def safe(s):
    """Make a string safe for use in a folder name."""
    s = (s or "").strip() or "unnamed"
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in s)[:40]


class Recorder:
    def __init__(self, folder_base, animal, session, session_id="TRAINING", note=""):
        self.animal, self.session = safe(animal), safe(session or "S1")
        self.session_id, self.note = session_id, note
        self.started = datetime.now()
        self.sub_folder = (f"{self.animal}_{self.session}_"
                           f"{self.started.strftime('%Y%m%d_%H%M%S')}")
        self.folder = os.path.join(folder_base, self.sub_folder)
        os.makedirs(self.folder, exist_ok=True)
        self.trials = []
        self.closed = False
        self.events_path = os.path.join(self.folder, "events.csv")
        self._ef = open(self.events_path, "w", newline="", encoding="utf-8")
        self._ew = csv.writer(self._ef)
        self._ew.writerow(["trial", "phase", "event_code", "event",
                           "ms_since_reset", "wall_clock"])
        self._ef.flush()

    def write_trial(self, itrial, events, events_before, t_events0, vars_, params):
        name_file = f"FUS_{itrial:02d}"
        md_ext = {"session": self.session, "animal": self.animal,
                  "class": PR.SESSIONS[self.session_id]["meta"]["class"],
                  "ntrial": itrial, "Ndelivery": vars_["Ndelivery"],
                  "Nflash": vars_["Nflash"]}
        payload = {"mdExt": md_ext,
                   "timeEvents0": t_events0.isoformat(timespec="milliseconds"),
                   "parameters": params, "Events": events, "EventsBefore": events_before}
        with open(os.path.join(self.folder, name_file + ".json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        now = datetime.now().isoformat(timespec="milliseconds")
        if not self.closed:
            for e in events_before:
                self._ew.writerow([itrial, "before", e["code"], e["name"], e["ms"], now])
            for e in events:
                self._ew.writerow([itrial, "trial", e["code"], e["name"], e["ms"], now])
            self._ef.flush()

        # descriptive summary - NOT a performance score
        drop = [e for e in events if e["name"] in ("DROP_ON", "AUDIODROP_ON")]
        touch = [e for e in events if e["name"] == "TOUCH_ON"]
        lat = None
        if drop and touch:
            after = [t["ms"] - drop[0]["ms"] for t in touch if t["ms"] >= drop[0]["ms"]]
            lat = after[0] if after else None
        summary = {"trial": itrial, "n_drop": len(drop), "n_touch": len(touch),
                   "n_touch_before": len([e for e in events_before if e["name"] == "TOUCH_ON"]),
                   "touch_after_drop_ms": lat, "file": name_file + ".json"}
        self.trials.append(summary)
        return summary

    def stats(self):
        n = len(self.trials)
        k = sum(1 for t in self.trials if t["touch_after_drop_ms"] is not None)
        lats = sorted(t["touch_after_drop_ms"] for t in self.trials
                      if t["touch_after_drop_ms"] is not None)
        return {"trials": n, "with_touch": k, "without_touch": n - k,
                "rate": (k / n) if n else 0.0,
                "median_latency_ms": lats[len(lats) // 2] if lats else None,
                "total_touch": sum(t["n_touch"] for t in self.trials),
                "total_drop": sum(t["n_drop"] for t in self.trials)}

    def outcomes(self):
        return [(t["touch_after_drop_ms"] is not None, "#2f9e78" if
                 t["touch_after_drop_ms"] is not None else "#c25a4f") for t in self.trials]

    def close(self, vars_=None, params=None, completed_all=False):
        if self.closed:
            return
        s = PR.SESSIONS[self.session_id]
        meta = {"animal": self.animal, "session": self.session,
                "session_id": self.session_id, "sub_folder": self.sub_folder,
                "note": self.note,
                "started": self.started.isoformat(timespec="seconds"),
                "finished": datetime.now().isoformat(timespec="seconds"),
                "completed_all_trials": completed_all,
                "source_file": s["source_file"],
                "variables": vars_ or PR.session_vars(self.session_id),
                "parameters": params or PR.session_params(self.session_id),
                "variable_sources": {k: v["source"] for k, v in s["vars"].items()},
                "parameter_sources": {k: v["source"] for k, v in s["params"].items()},
                "firmware": "Droplet_Dispenser_V05.ino (unmodified)",
                "summary": self.stats(), "trials": self.trials}
        with open(os.path.join(self.folder, "session.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        try:
            self._ef.close()
        except Exception:
            pass
        self.closed = True
