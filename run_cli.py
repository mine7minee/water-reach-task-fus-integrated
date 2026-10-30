#!/usr/bin/env python3
"""Water Reach Task - run the Tinkerforge cue-reward task WITHOUT the GUI.

Examples
    python run_cli.py --animal M01 --session S1
    python run_cli.py --animal M01 --session S1 --trials 20
    python run_cli.py --animal M01 --host 192.168.1.50

Stop at any time with Ctrl+C - completed trials are already saved.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wrt import config as C                     # noqa: E402
from wrt.tf_rig import TinkerforgeRig           # noqa: E402
from wrt.tf_task import TFRecorder, TFTaskRunner  # noqa: E402


def main():
    cfg = C.load()
    ap = argparse.ArgumentParser(description="Tinkerforge cue-reward task (no GUI)")
    ap.add_argument("--animal", required=True, help="animal ID, e.g. M01")
    ap.add_argument("--session", default="S1", help="session ID (default S1)")
    ap.add_argument("--note", default="", help="free text note")
    ap.add_argument("--trials", type=int, default=None,
                    help=f"number of trials (default {cfg['task']['total_trials']})")
    ap.add_argument("--host", default=None, help="rig address (default from config.json)")
    ap.add_argument("--out", default=None, help="output folder (default Downloads/WaterReachTask)")
    a = ap.parse_args()

    params = dict(cfg["task"])
    if a.trials:
        params["total_trials"] = a.trials
    tf = dict(cfg["tinkerforge"])
    if a.host:
        tf["host"] = a.host
    out = a.out or C.output_dir(cfg)

    print("=" * 52)
    print(" Water Reach Task - Tinkerforge cue-reward task")
    print("=" * 52)
    for k, v in params.items():
        print(f"  {k:<24} {v}")
    print("=" * 52)

    rig = TinkerforgeRig(tf, cfg["relay_channels"])
    rig.connect()
    for line in rig.device_summary():
        print("  " + line)

    rec = TFRecorder(out, a.animal, a.session, a.note, params)
    print(f"\nData folder: {rec.folder}")
    input("Press Enter to start (Ctrl+C stops the session) ... ")

    done = {"flag": False, "all": False}

    def emit(kind, p):
        if kind == "trial_start":
            print(f"\n--- TRIAL {p['trial']}/{p['ntrials']} | LED: {p['led']} ---")
        elif kind == "log":
            print("  " + p["text"].split(": ", 1)[-1])
        elif kind == "error":
            print("ERROR:", p["message"])
        elif kind == "finished":
            done["all"] = p.get("completed_all", False)
            done["flag"] = True

    runner = TFTaskRunner(rig, rec, emit, params)
    runner.start()
    try:
        while not done["flag"]:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping ...")
        runner.stop()
        runner.join(10)

    rec.close(completed_all=done["all"])
    rig.close()
    st = rec.stats()
    print("\n" + "=" * 52)
    print(" SUMMARY")
    print("=" * 52)
    print(f"  Trials completed   : {st['all']['trials']}/{params['total_trials']}")
    print(f"  Trials with licks  : {st['all']['licked']} ({st['all']['rate']*100:.1f}%)")
    print(f"  BLUE  with licks   : {st['BLUE']['licked']}/{st['BLUE']['trials']}")
    print(f"  GREEN with licks   : {st['GREEN']['licked']}/{st['GREEN']['trials']}")
    print(f"  Total licks        : {st['all']['licks']}")
    print(f"\n  Saved in: {rec.folder}")


if __name__ == "__main__":
    main()
