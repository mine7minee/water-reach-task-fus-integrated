#!/usr/bin/env python3
"""List every Tinkerforge device the rig reports, with its UID and port.

    python tools/find_devices.py            (address from config.json, default 'auto')
    python tools/find_devices.py 192.168.1.50
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wrt import config as C                                     # noqa: E402
from wrt.tf_rig import DEVICE_NAMES, TinkerforgeRig, detect_gateways  # noqa: E402

cfg = C.load()
tf = dict(cfg["tinkerforge"])
if len(sys.argv) > 1:
    tf["host"] = sys.argv[1]
print("Default gateways found:", ", ".join(detect_gateways()) or "none")
rig = TinkerforgeRig(tf, cfg["relay_channels"])
try:
    rig.connect()
except Exception as e:
    print("\n" + str(e))
    sys.exit(1)
print(f"\nRig address: {rig.host}\n")
for uid, (dev, pos) in sorted(rig.found.items(), key=lambda x: str(x[1][1])):
    print(f"  Port {pos:<3} UID {uid:<8} {DEVICE_NAMES.get(dev, f'device type {dev}')}")
rig.close()
print("\nThese values are found automatically - you do not need to copy them anywhere.")
