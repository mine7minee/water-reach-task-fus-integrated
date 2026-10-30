# Arduino droplet dispenser and camera shuttle

This part of the software is a Python port of the lab's MATLAB control layer.
The Arduino firmware **`Droplet_Dispenser_V05.ino` is not modified**.

## MATLAB → Python

| MATLAB | Python |
|---|---|
| `commDropplet.m` | `wrt/dispenser.py` |
| `commProtocol.m` | `wrt/camera.py` |
| `waitNoTuch.m` | `wrt/training.py` → `wait_no_touch()` |
| `MultistimObject.m` | `wrt/training.py` → `TrainingRunner._new_image()` |
| `exp_Training.m` | `wrt/training.py` → `TrainingRunner` |
| `initProtocol.m` | `wrt/params.py` |
| `droppletApp.mlapp`, `testdropplet.m` | Tools tab (manual commands) |
| `exp_Fus.m`, `exp_Dropplet.m` | **not ported** — they drive the Verasonics scanner (`SCAN.doppler`) |

`trackingSession()` / `fService()` (central database) have no Python
equivalent: animal and session IDs are typed in the window and written to
`session.json`.

## Training session (exp_Training.m)

```
camera setName 'CAM_nn' ; setIdn
dispenser ResetTime
waitNoTuch(5 s)             trial starts only after 5 s without touch
EventsBefore = history
camera start ; dispenser ResetTime
for image = 1..20
    camera tagImage
    if image == 10 -> AudioDelayDrop
    pause 0.7 s
end
Events = history ; camera stop ; save FUS_nn
```

On `AudioDelayDrop` the firmware plays the sound (350 ms), waits (100 ms) and
opens the valve (120 ms).

| Parameter | initProtocol.m | exp_Training.m | exp_Fus.m | exp_Dropplet.m |
|---|---|---|---|---|
| ParDropSize (ms) | 100 | **120** | 100 | 2300 |
| ParAudioDuration (ms) | 350 | **350** | 350 | — |
| ParDelayAudioDrop (ms) | 1000 | **100** | 100 | — |

Firmware defaults (.ino): DropSize 100, AudioDuration 50, DelayAudioDrop 0,
FreqAudio 8000 Hz (fixed).

## Wire protocol

| | MATLAB | Python |
|---|---|---|
| Command | `fwrite(uint8(cmd))` + `fwrite(int16(val),'int16')` | `struct.pack("<Bh", cmd, val)` — always 3 bytes |
| Event | `uint8` + `uint32`, 5 bytes | same |
| Baud | 9600 | 9600 |

Command codes: Dropplet 1, Flush 2, ParDropSize 5, ParAudioDuration 7,
ParDelayAudioDrop 8, Audio 10, AudioAndDrop 11, ResetCount 12, AudioDelayDrop 13.
Event codes: drop 1/10, audio 2/20, audio+drop 3/30, touch 4/40 (on/off).

## Known issues in the MATLAB code (kept, documented only)

* **Nflash is ignored** — the firmware's `AudioDelayDrop` does not read the
  argument; it always plays one sound and delivers one drop.
* **ParAspTime does not exist** in firmware V05 (`exp_Dropplet.m` sends it; it is ignored).
* **Unit comments are wrong** — MATLAB comments say microseconds; the firmware
  uses milliseconds (2300 in `exp_Dropplet.m` = 2.3 s of valve opening).
* **Flush argument is milliseconds**, not "number of cycles".
* **Event history is silently cut at 10 000 events** in `commDropplet.m`. The
  Python version has no limit.
* **COM port numbers differ** between the MATLAB files — choose the port in the window.
* **DelayAudioDrop** is 1000 in `initProtocol.m` but 100 in the session files
  (the session value wins).

## To verify before animal work

How many microlitres one `ParDropSize` value delivers is not documented —
calibrate with the Tools tab (section 8 of the README).
