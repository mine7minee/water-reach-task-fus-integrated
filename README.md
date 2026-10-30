# Water Reach Task — fUS Integrated

**Author:** Meryem Mine Kurum
**Version:** 1.0.0
**Platform:** Windows 10 / 11 (also runs on macOS and Linux)

Control software for a head-fixed **water reaching / licking task** used with
functional ultrasound (fUS) imaging. One program drives two kinds of hardware:

| Back-end | Hardware | What it does |
|---|---|---|
| **Tinkerforge rig** (main) | ESP32 Brick + Bricklets, connected over WiFi | Beep, random blue/green cue LED, water valve, lick sensor |
| **Arduino dispenser** (optional) | Droplet dispenser Arduino + camera shuttle, connected over USB | Python version of the lab's MATLAB training session (`exp_Training.m`) |

Everything is controlled from a simple window with three tabs. All data are
saved automatically after every trial, so nothing is lost if the session is
stopped early or the computer crashes.

This guide assumes **no programming experience**. Follow the sections in order.

---

## Contents

1. [What happens in one trial](#1-what-happens-in-one-trial)
2. [Hardware](#2-hardware)
3. [Installation (once per computer)](#3-installation-once-per-computer)
4. [Before every experiment day](#4-before-every-experiment-day)
5. [Running a session](#5-running-a-session)
6. [Output files](#6-output-files)
7. [Changing the task settings](#7-changing-the-task-settings)
8. [Water calibration](#8-water-calibration)
9. [Arduino dispenser and camera (optional)](#9-arduino-dispenser-and-camera-optional)
10. [Troubleshooting](#10-troubleshooting)
11. [Folder contents](#11-folder-contents)
12. [Privacy: what is never uploaded](#12-privacy-what-is-never-uploaded)

---

## 1. What happens in one trial

Default settings — **50 trials, 15 s each**:

```
 time (s)   0     3           6   6.3         9                      15
            |-----|-----------|---|-----------|-----------------------|
 beep       ■
 cue LED          ███████████████████████████   (BLUE or GREEN, random)
 valve                        ■■■               (0.3 s water reward)
 lick sensor  ◄──────────── recorded for the whole 15 s ────────────►
```

| Time | Event |
|---|---|
| 0.0 s | Beep (1000 Hz, 0.5 s) — marks the start of the trial |
| 3.0 s | Cue LED switches on. The colour (blue or green) is chosen at random each trial |
| 6.0 s | Valve opens for 0.3 s — water reward |
| 9.0 s | Cue LED switches off |
| 15.0 s | Trial ends; 0.5 s pause; the next trial starts |

Every lick (each new touch of the metal spout) is counted and time-stamped.

---

## 2. Hardware

### Tinkerforge rig

| Part | Tinkerforge SKU | Job |
|---|---|---|
| ESP32 Brick | 113 | Main controller, WiFi |
| ESP32 Power Supply | 42 | Powers the brick from the 12 V supply (stacked under the brick) |
| Piezo Speaker Bricklet 2.0 | 2145 | Beep |
| Industrial Quad Relay Bricklet 2.1 | 2102 | Switches the LEDs and the valve |
| Multi Touch Bricklet 2.0 | 2129 | Lick sensor (metal spout) |
| Industrial Digital In 4 Bricklet 2.0 | 2100 | Spare / camera sync input |
| 12 V / 2 A power adapter | — | Power for everything |
| 12 V solenoid valve (NC, ≤ 0.6 A) | — | Water reward |
| 12 V blue LED, 12 V green LED | — | Visual cues |
| 1N4007 diode | — | Protects the relay from the valve's voltage spike |

The Bricklets can be plugged into **any** port of the ESP32 Brick — the
software finds them automatically.

### Relay channels (Quad Relay 2.1)

| Channel | Connected to |
|---|---|
| CH0 | spare |
| CH1 | Blue LED |
| CH2 | Water valve (with 1N4007 diode across it) |
| CH3 | Green LED |

> ⚠️ The Quad Relay 2.1 is **polarity-sensitive**: +12 V goes to the (+)
> terminal of a channel, the device goes to the (−) terminal. Reversed wiring
> means the output does not switch.

Full wiring instructions: [`docs/WIRING.md`](docs/WIRING.md) and the diagram
[`docs/Tinkerforge_SensoryRig_Wiring.pdf`](docs/Tinkerforge_SensoryRig_Wiring.pdf).

---

## 3. Installation (once per computer)

Takes about 15 minutes. You need administrator rights only for installing Python.

### Step 3.1 — Install Python

1. Go to <https://www.python.org/downloads/windows/> and download **Python 3.11**
   or newer ("Windows installer (64-bit)").
2. Run the installer. On the first screen **tick "Add python.exe to PATH"**,
   then click **Install Now**.
3. Check: press the Windows key, type `cmd`, press Enter, and type:

   ```cmd
   python --version
   ```

   You should see `Python 3.11.x` (or newer).

### Step 3.2 — Download this project

**Option A (no Git needed):** on the GitHub page click the green **Code** button
→ **Download ZIP**. Right-click the downloaded file → **Extract All**. Move the
extracted folder somewhere easy to find, for example your **Documents** folder.

**Option B (with Git):**

```cmd
cd %USERPROFILE%\Documents
git clone https://github.com/mine7minee/water-reach-task-fus-integrated.git
```

### Step 3.3 — Run the setup

Open the project folder and **double-click `setup_windows.bat`**.

It creates a private Python environment (`.venv`) inside the folder and
installs the three required packages (`tinkerforge`, `openpyxl`, `pyserial`).
Wait for **"Setup complete"**, then press any key.

If you prefer the command line, this does the same:

```cmd
cd <project folder>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3.4 — Prepare the ESP32 Brick (only for a brand-new brick)

Skip this if the rig has been used before.

1. Install **Brick Viewer** from <https://www.tinkerforge.com/en/doc/Downloads.html>.
   (Brick Daemon is **not** needed — the ESP32 Brick talks to the PC directly over WiFi.)
2. Connect the ESP32 Brick to the PC with a USB-C cable.
3. Brick Viewer → **Updates / Flashing** → **Brick** tab → select the
   ESP32 Brick's COM port → firmware **ESP32** → **Flash**.
   Wait until the blue status LED blinks (up to 60 s).
4. The brick now opens its own WiFi network called **`esp32-XXXX`**
   (XXXX is printed on the brick). Connect the PC to this network.
5. Open the brick's web interface (in Brick Viewer: select the ESP32 Brick tab →
   **Open ESP32 Brick Web Interface**). Under **Network → Access Point** set a
   WiFi password of your own and write it in your lab's password store
   — never in this project.

> **Why the brick's own WiFi?** University networks (eduroam, campus WiFi)
> use username + password logins that the ESP32 cannot join. The brick's own
> access point always works. While the PC is connected to it, the PC has no
> internet over WiFi — use a network cable if you need internet at the same time.

---

## 4. Before every experiment day

1. **Power:** plug in the 12 V adapter. Wait ~30 s until the ESP32 status LED blinks.
2. **WiFi:** connect the PC to the brick's network `esp32-XXXX`
   (Windows: WiFi icon at the bottom right).
3. **Hardware check:** double-click **`HARDWARE_CHECK.bat`**. It beeps, flashes
   each LED, clicks the valve three times and asks you to touch the spout. Answer
   the questions with `y` or `n`. Everything should say **OK**.
4. **Water:** fill the reservoir at the same height as during calibration and
   flush the line until no air bubbles are left (Tools tab → *Valve pulse*).

---

## 5. Running a session

Double-click **`START.bat`**. The program window opens.

### Tab 1 — Setup

| Box | What to do |
|---|---|
| **A. Tinkerforge rig** | Leave the address on `auto` and click **CONNECT RIG**. After a few seconds you see "Connected" and a list of the Bricklets found. |
| **B. Arduino dispenser + camera** | Only needed for the Arduino session or for camera triggering — see section 9. |
| **C. Animal and session** | Type the **Animal ID** (required, e.g. `M01`) and a **Session ID** (e.g. `S1` or `Day3`). Optional note. |
| **D. Data folder** | Where results go. Default: `Downloads\WaterReachTask`. Click **Change** to pick another folder. |

### Tab 2 — Session

1. Select **Cue-reward task (Tinkerforge rig)**.
2. Check the parameters (number of trials, timings). Defaults are shown; any
   change applies to this session only and is saved with the data.
3. Click **START**.

During the session the window shows the current trial, the cue colour, the
licks in this trial, the number of trials with licks, the success rate and a
running plot. Each bar is one trial (**tall bar = the animal licked**; blue or
green = cue colour). The line is the lick rate over the last 20 trials.

Click **STOP** at any time. The current (unfinished) trial is discarded; all
completed trials are already saved. A summary window appears at the end.

### Tab 3 — Tools

Manual buttons for testing: beep, blue / green LED on/off, single valve pulse,
N valve pulses (calibration), all outputs off, and a live lick indicator
(the dot turns green when the spout is touched).

### Without the window (command line)

```cmd
cd <project folder>
.venv\Scripts\activate
python run_cli.py --animal M01 --session S1
```

Optional: `--trials 20`, `--note "first day"`, `--host <address>`.
Stop with **Ctrl+C**.

---

## 6. Output files

Each session creates one folder:

```
Downloads\WaterReachTask\
└── M01_S1_20261030_143012\        <animal>_<session>_<date>_<time>
    ├── session.xlsx               open with Excel
    ├── licks.csv                  every single lick (for R / Python / MATLAB)
    └── session.json               all settings + summary (machine-readable)
```

### `session.xlsx`

**Sheet "Trial Data"** — one row per trial (blue rows = blue cue, green rows = green cue):

| Column | Meaning |
|---|---|
| Trial | Trial number |
| LED | Cue colour (BLUE / GREEN) |
| Licked | 1 = at least one lick in this trial, 0 = none |
| Lick Count | Number of licks in the trial |
| First Lick (s) | Time of the first lick, seconds after trial start |
| Licks Before LED | Licks before the cue came on (0 – 3 s) |
| Licks LED On | Licks while the cue was on (3 – 9 s, includes the reward at 6 s) |
| Licks After LED | Licks after the cue went off (9 – 15 s) |
| Trial Duration (s) | Measured length of the trial |
| Log | Every event of the trial with its time |

**Sheet "Summary"** — totals for all trials, for blue trials and for green
trials, plus every parameter used.

**Sheet "Log"** — every event of the session with clock time.

### `licks.csv`

| trial | led | lick_number | time_in_trial_s |
|---|---|---|---|
| 1 | BLUE | 1 | 6.412 |

---

## 7. Changing the task settings

Default settings are stored in **`config.json`** in the project folder (created
automatically on first start). Open it with Notepad, change a number, save, and
restart the program. The values can also be changed per session in tab 2.

| Setting | Default | Meaning |
|---|---|---|
| `total_trials` | 50 | Trials per session |
| `trial_duration_s` | 15.0 | Length of one trial (s) |
| `led_start_s` | 3.0 | Cue LED on (s after trial start) |
| `led_duration_s` | 6.0 | How long the cue stays on (s) |
| `valve_time_s` | 6.0 | Reward time (s after trial start) |
| `valve_duration_s` | 0.3 | Valve open time (s) — controls the reward size |
| `inter_trial_interval_s` | 0.5 | Pause between trials (s) |
| `beep_frequency_hz` | 1000 | Beep pitch (50 – 15000 Hz) |
| `beep_volume` | 5 | 0 – 10. Start low; 10 is very loud |
| `beep_duration_ms` | 500 | Beep length (ms) |
| `lick_electrode` | 0 | Multi Touch electrode wired to the spout |
| `lick_poll_interval_s` | 0.05 | Lick sensor read every 50 ms |

Other sections of `config.json`:

* `tinkerforge.host` — `auto` (recommended) or the brick's address.
  `uid_piezo`, `uid_relay`, `uid_touch` can stay empty (automatic detection).
* `relay_channels` — which relay channel drives which device.
* `output_dir` — data folder; empty = `Downloads\WaterReachTask`.

> If `config.json` gets broken, delete it — a fresh copy is created from
> `config.example.json` on the next start.

---

## 8. Water calibration

The reward size depends on valve open time, tubing and reservoir height.
Measure it whenever the setup changes:

1. Put a small cup on a balance under the spout and press **tare**.
2. Tab 3 → set *Valve pulse (s)* (e.g. 0.3) and *Pulses for calibration* (e.g. 50)
   → **Run N pulses**.
3. Read the weight in mg (1 mg of water = 1 µL), type it into
   *Weight (mg)* in the calibration box → **Save measurement**.

The table shows µL per reward and is stored in `calibration.json` in the data folder.

---

## 9. Arduino dispenser and camera (optional)

The project also contains a Python version of the lab's MATLAB control layer
for the **Arduino droplet dispenser** (`Droplet_Dispenser_V05.ino`, unchanged)
and the **camera shuttle**.

* **Arduino training session:** Tab 1 box B → *Scan ports* → choose the ports →
  **Connect dispenser**. Tab 2 → *Arduino dispenser training* → START.
  Output per trial: `FUS_01.json`, `FUS_02.json` … plus `events.csv` and
  `session.json` (same content as the MATLAB `save()` files; read in MATLAB with
  `jsondecode(fileread('FUS_01.json'))`).
* **Camera with the Tinkerforge task:** connect only the camera
  (**Connect camera only**). Each trial is then sent to the camera as
  `CAM_01`, `CAM_02` … with start/stop markers.
* **fUS imaging sessions** (`exp_Fus.m`, `exp_Dropplet.m`) control the
  Verasonics scanner and must still be run from MATLAB.

Protocol details and known issues of the MATLAB code:
[`docs/ARDUINO_DISPENSER.md`](docs/ARDUINO_DISPENSER.md).

---

## 10. Troubleshooting

| Problem | Solution |
|---|---|
| `python` is not recognized | Python was installed without "Add to PATH". Re-run the Python installer → *Modify* → tick *Add Python to environment variables*. |
| `setup_windows.bat` fails at "Installing packages" | Needs internet. Connect to a normal network (not the ESP32 WiFi), run it again. |
| "Rig not found" | Is the 12 V supply on and the ESP32 LED blinking? Is the PC connected to the `esp32-XXXX` WiFi? Wait 30 s after power-on and try again. |
| Rig still not found with `auto` | Find the brick's address: in `cmd` type `ipconfig` and read **Default Gateway** of the WiFi adapter. Type that address into the *Address* box instead of `auto`. |
| "Bricklet(s) not found: relay" (or piezo/touch) | A Bricklet cable is loose. Re-seat both ends, power-cycle, reconnect. Run `python tools\find_devices.py` to list what the brick sees. |
| Valve does not open | Check +12 V on CH2(+), polarity, and the 1N4007 direction (stripe toward the wire coming from CH2 (−)). Test the valve directly on 12 V. |
| LED does not light | Check +12 V on CH1(+) / CH3(+) and the LED's black wire to GND. |
| Licks not detected | Tab 3 → touch the spout and watch the dot. Check the jumper wire on electrode 0. Make sure the spout does not touch metal parts of the frame. |
| Lick sensor always "TOUCH" | Water bridge or wet spout holder. Dry the area; restart the program (the sensor recalibrates at power-on). |
| WiFi drops during a session | The software reconnects automatically and continues. Keep the PC within a few metres of the rig. |
| "Permission denied" when saving Excel | `session.xlsx` is open in Excel. Data is saved to `session_autosave.xlsx` instead; close Excel. |

---

## 11. Folder contents

```
water-reach-task-fus-integrated/
├── README.md                  this guide
├── setup_windows.bat          one-time installation (double-click)
├── START.bat                  open the program (double-click)
├── HARDWARE_CHECK.bat         test the rig without an animal (double-click)
├── run.py                     starts the window
├── run_cli.py                 runs the Tinkerforge task without the window
├── config.example.json        template for config.json (your local settings)
├── requirements.txt           Python packages
├── wrt/                       program code
│   ├── gui.py                 the window
│   ├── tf_rig.py              Tinkerforge hardware (auto-discovery)
│   ├── tf_task.py             cue-reward task + Excel/CSV/JSON output
│   ├── config.py              settings loader
│   ├── params.py              task and MATLAB session parameters
│   ├── dispenser.py           Arduino dispenser   (commDropplet.m)
│   ├── camera.py              camera shuttle      (commProtocol.m)
│   ├── training.py            training session    (exp_Training.m)
│   ├── recorder.py            Arduino session files
│   ├── proto.py               Arduino wire protocol
│   └── theme.py               colours and fonts
├── tools/
│   ├── hardware_check.py      guided hardware test
│   └── find_devices.py        list the Bricklets the brick reports
└── docs/
    ├── WIRING.md              wiring step by step
    ├── Tinkerforge_SensoryRig_Wiring.pdf
    ├── ARDUINO_DISPENSER.md   Arduino protocol + MATLAB notes
    └── GITHUB_UPLOAD.md       how to publish / update this repository
```

---

## 12. Privacy: what is never uploaded

`.gitignore` keeps these files on your computer only:

| File / folder | Why |
|---|---|
| `config.json` | Your rig's network address and device IDs |
| `.venv/` | Local Python installation (large, computer-specific) |
| `data/`, `*.xlsx`, `*.csv`, `session.json`, `calibration.json` | Animal data |

The code contains **no** IP addresses, device IDs, passwords or personal paths:
the rig is found automatically at run time.

---

## License

For internal lab use. Please contact the author before redistributing.
