"""
Session definitions.

TF_CUE      - Tinkerforge cue-reward task (timing from config.json "task").
TRAINING    - Arduino dispenser training, port of exp_Training.m.
FUS, DROPPLET - listed for reference only: they drive the Verasonics
                scanner (SCAN.doppler) and must run in MATLAB.

Values for the MATLAB-derived sessions are copied unchanged from the lab's
files; the "source" field records where each value comes from.
"""

# ---------------------------------------------------------------------
# Tinkerforge task - editable fields shown in the GUI
# (key, label, type, help text)
# ---------------------------------------------------------------------
TF_FIELDS = [
    ("total_trials",           "Number of trials",          int,   "trials per session"),
    ("trial_duration_s",       "Trial duration (s)",        float, "total length of one trial"),
    ("led_start_s",            "LED on at (s)",             float, "cue LED (blue or green, random) turns on"),
    ("led_duration_s",         "LED duration (s)",          float, "how long the cue LED stays on"),
    ("valve_time_s",           "Valve opens at (s)",        float, "water reward time"),
    ("valve_duration_s",       "Valve open time (s)",       float, "0.3 = 300 ms"),
    ("inter_trial_interval_s", "Inter-trial interval (s)",  float, "pause between trials"),
    ("beep_frequency_hz",      "Beep frequency (Hz)",       int,   "50 - 15000; beep at trial start"),
    ("beep_volume",            "Beep volume (0-10)",        int,   "start low; 10 is very loud"),
    ("beep_duration_ms",       "Beep duration (ms)",        int,   ""),
    ("lick_electrode",         "Lick electrode (0-11)",     int,   "Multi Touch electrode wired to the spout"),
    ("lick_poll_interval_s",   "Lick poll interval (s)",    float, "0.05 = sensor read 20x per second"),
]

# ---------------------------------------------------------------------
# Arduino dispenser sessions (from the lab's MATLAB files)
# ---------------------------------------------------------------------
SESSIONS = {
    "TRAINING": {
        "name": "Arduino dispenser training  (exp_Training.m)",
        "source_file": "exp_Training.m",
        "runnable_in_python": True,
        "vars": {
            "nimag":      {"value": 20,  "source": "exp_Training.m:3",
                           "note": "number of 'images' (time bins) per trial"},
            "ntrials":    {"value": 100, "source": "exp_Training.m:4"},
            "Ndelivery":  {"value": 10,  "source": "exp_Training.m:5",
                           "note": "image number at which the drop is delivered"},
            "Nflash":     {"value": 1,   "source": "exp_Training.m:6",
                           "note": "AudioDelayDrop argument - ignored by firmware V05"},
            "timeNoTuch": {"value": 5,   "source": "exp_Training.m:10",
                           "note": "seconds without touch required before a trial starts"},
            "image_pause": {"value": 0.7, "source": "exp_Training.m:73 -> pause(0.7)",
                            "note": "seconds between images"},
        },
        "params": {
            "ParDropSize":       {"value": 120, "source": "exp_Training.m:14",
                                  "note": "valve open time, ms"},
            "ParAudioDuration":  {"value": 350, "source": "exp_Training.m:15",
                                  "note": "sound duration, ms (8 kHz fixed in firmware)"},
            "ParDelayAudioDrop": {"value": 100, "source": "exp_Training.m:16",
                                  "note": "delay sound -> drop, ms"},
        },
        "meta": {"class": "trining"},      # spelling kept as in the MATLAB file
    },
    "FUS": {
        "name": "fUS recording  (exp_Fus.m) - MATLAB only",
        "source_file": "exp_Fus.m",
        "runnable_in_python": False,
        "vars": {
            "nimag":      {"value": 40,  "source": "exp_Fus.m:3"},
            "ntrials":    {"value": 100, "source": "exp_Fus.m:4"},
            "Ndelivery":  {"value": 10,  "source": "exp_Fus.m:5"},
            "Nflash":     {"value": 1,   "source": "exp_Fus.m:6"},
            "frameTime":  {"value": 16,  "source": "exp_Fus.m:7",
                           "note": "units of 0.05 s -> 0.8 s per image"},
            "timeNoTuch": {"value": 5,   "source": "exp_Fus.m:8"},
        },
        "params": {
            "ParDropSize":       {"value": 100, "source": "exp_Fus.m:10"},
            "ParAudioDuration":  {"value": 350, "source": "exp_Fus.m:11"},
            "ParDelayAudioDrop": {"value": 100, "source": "exp_Fus.m:12"},
        },
        "meta": {"class": "trial"},
    },
    "DROPPLET": {
        "name": "Drop test  (exp_Dropplet.m) - MATLAB only",
        "source_file": "exp_Dropplet.m",
        "runnable_in_python": False,
        "vars": {
            "nimag":     {"value": 20, "source": "exp_Dropplet.m:3"},
            "ntrials":   {"value": 10, "source": "exp_Dropplet.m:4"},
            "Ndelivery": {"value": 10, "source": "exp_Dropplet.m:5"},
            "Nflash":    {"value": 5,  "source": "exp_Dropplet.m:6"},
        },
        "params": {
            "ParDropSize": {"value": 2300, "source": "exp_Dropplet.m:11"},
        },
        "meta": {"class": "trial"},
    },
}

FIRMWARE_DEFAULTS = {"ParDropSize": 100, "ParAudioDuration": 50, "ParDelayAudioDrop": 0}
FLUSH_MS = 500


def session_params(session_id):
    s = SESSIONS[session_id]
    return {k: v["value"] for k, v in s["params"].items()
            if k in ("ParDropSize", "ParAudioDuration", "ParDelayAudioDrop")}


def session_vars(session_id):
    return {k: v["value"] for k, v in SESSIONS[session_id]["vars"].items()}
