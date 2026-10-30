#!/usr/bin/env python3
"""Step-by-step hardware check of the Tinkerforge rig (no animal).

Run after wiring or before an experiment day:
    python tools/hardware_check.py

Sequence: beep -> blue LED 1 s -> green LED 1 s -> valve 3 short pulses
          -> 10 s lick-sensor test (touch the spout with a finger).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wrt import config as C                 # noqa: E402
from wrt.tf_rig import TinkerforgeRig       # noqa: E402


def ask(q):
    return input(f"  {q} [y/n] ").strip().lower().startswith("y")


cfg = C.load()
p = cfg["task"]
rig = TinkerforgeRig(cfg["tinkerforge"], cfg["relay_channels"])
rig.connect()
rig.configure_touch(p["lick_electrode"])
results = {}
try:
    print("\n1) Beep")
    rig.beep(p["beep_frequency_hz"], p["beep_volume"], p["beep_duration_ms"])
    time.sleep(0.8)
    results["beep"] = ask("Did you hear the beep?")

    print("\n2) Blue LED (relay channel %d)" % cfg["relay_channels"]["blue_led"])
    rig.set_outputs(blue=True); time.sleep(1.0); rig.set_outputs(blue=False)
    results["blue_led"] = ask("Did the BLUE LED light up?")

    print("\n3) Green LED (relay channel %d)" % cfg["relay_channels"]["green_led"])
    rig.set_outputs(green=True); time.sleep(1.0); rig.set_outputs(green=False)
    results["green_led"] = ask("Did the GREEN LED light up?")

    print("\n4) Valve (relay channel %d) - 3 pulses" % cfg["relay_channels"]["valve"])
    for _ in range(3):
        rig.valve_pulse(p["valve_duration_s"]); time.sleep(0.5)
    results["valve"] = ask("Did the valve click / did water come out?")

    print("\n5) Lick sensor - touch the spout a few times during the next 10 s")
    n, last, t0 = 0, False, time.time()
    while time.time() - t0 < 10:
        now = rig.read_lick()
        if now and not last:
            n += 1
            print(f"     touch #{n}")
        last = now
        time.sleep(p["lick_poll_interval_s"])
    results["lick_sensor"] = n > 0
finally:
    rig.all_off()
    rig.close()

print("\n" + "=" * 40)
for k, ok in results.items():
    print(f"  {k:<12} {'OK' if ok else 'CHECK WIRING'}")
print("=" * 40)
if not all(results.values()):
    print("See README.md -> Troubleshooting and docs/WIRING.md")
