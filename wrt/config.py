"""Local configuration.

Settings live in ``config.json`` in the project folder. That file is created
automatically from ``config.example.json`` the first time the software runs
and is excluded from git (see .gitignore), so your rig's network address and
device IDs never end up on GitHub.
"""
import copy
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")
EXAMPLE_PATH = os.path.join(ROOT, "config.example.json")

DEFAULTS = {
    "tinkerforge": {"host": "auto", "port": 4223,
                    "uid_piezo": "", "uid_relay": "", "uid_touch": ""},
    "relay_channels": {"blue_led": 1, "valve": 2, "green_led": 3},
    "task": {
        "total_trials": 50,
        "trial_duration_s": 15.0,
        "led_start_s": 3.0,
        "led_duration_s": 6.0,
        "valve_time_s": 6.0,
        "valve_duration_s": 0.3,
        "inter_trial_interval_s": 0.5,
        "beep_frequency_hz": 1000,
        "beep_volume": 5,
        "beep_duration_ms": 500,
        "lick_electrode": 0,
        "lick_poll_interval_s": 0.05,
    },
    "serial": {"dispenser_port": "", "camera_port": ""},
    "output_dir": "",
}


def _merge(base, extra):
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    """Return the merged configuration (defaults + config.json)."""
    if not os.path.exists(CONFIG_PATH) and os.path.exists(EXAMPLE_PATH):
        shutil.copyfile(EXAMPLE_PATH, CONFIG_PATH)
    user = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                user = json.load(f)
        except Exception as e:
            print(f"WARNING: could not read config.json ({e}); using defaults.")
    return _merge(DEFAULTS, user)


def save(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def output_dir(cfg):
    """Where session folders are written. Default: Downloads/WaterReachTask."""
    d = (cfg.get("output_dir") or "").strip()
    if not d:
        d = os.path.join(os.path.expanduser("~"), "Downloads", "WaterReachTask")
    os.makedirs(d, exist_ok=True)
    return d
