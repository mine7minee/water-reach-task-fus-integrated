# Wiring — Tinkerforge Sensory Rig

Diagram: [`Tinkerforge_SensoryRig_Wiring.pdf`](Tinkerforge_SensoryRig_Wiring.pdf)

Work with the 12 V adapter **unplugged**. Use proper stranded wire
(≥ 0.5 mm² / 20 AWG) for everything that carries 12 V; thin Dupont jumpers
are only for the lick-sensor signal.

## 1. Power

1. Stack the **ESP32 Power Supply** onto the **ESP32 Brick** (pin headers, no cable).
2. 12 V adapter → a **12 V distribution terminal block** and a **GND terminal block**
   (one input, several outputs each). Every 12 V device takes its own wire from these blocks.
3. 12 V block → ESP32 Power Supply **VIN**; GND block → ESP32 Power Supply **GND**.

## 2. Bricklet cables (7-pin, 15 cm)

Plug each Bricklet into any free port of the ESP32 Brick. The software finds
them by type, so the port letter does not matter.

| Bricklet | Purpose |
|---|---|
| Piezo Speaker 2.0 | beep — no other wiring |
| Industrial Quad Relay 2.1 | LEDs + valve |
| Multi Touch 2.0 | lick sensor |
| Industrial Digital In 4 2.0 | spare / camera sync (CH0) |

## 3. Quad Relay 2.1 — screw terminal

Each channel has a **(+)** and a **(−)** screw. The relay is solid-state and
**polarity-sensitive**: (+) always receives +12 V, (−) goes to the device.

| Channel | (+) screw | (−) screw | Device return wire |
|---|---|---|---|
| CH0 | — | — | spare |
| CH1 | +12 V block | Blue LED red wire | Blue LED black wire → GND block |
| CH2 | +12 V block | Valve wire A | Valve wire B → GND block |
| CH3 | +12 V block | Green LED red wire | Green LED black wire → GND block |

### Valve protection diode (1N4007) — required

A solenoid produces a voltage spike when it switches off; the diode absorbs it.

* Connect the diode **in parallel with the valve**, directly at the valve's two wires.
* **Stripe end (cathode)** → valve wire A (the wire coming from CH2 (−)).
* **Plain end (anode)** → valve wire B (the wire going to GND).

The 12 V pinch valve itself is not polarity-sensitive, but with the diode
fitted the orientation above must be respected.

The relay channel limit is **0.6 A**; the 075P2NC12 pinch valve draws about 0.29 A.

## 4. Lick sensor (Multi Touch 2.0)

* Female Dupont jumper on **electrode 0**; other end clipped to the metal spout
  (alligator clip).
* All other electrodes stay unconnected (the software disables them).
* The sensor calibrates itself at power-on: switch the rig on **with the spout
  in its final position and dry**.

## 5. Camera sync (optional, Digital In 4)

Camera sync output → BNC-to-screw adapter → **CH0** (+) and GND.
The input needs ≥ 3 V for "high". The current task does not record this input yet.

## 6. First power-on check

1. Plug in the 12 V adapter; ESP32 status LED should blink after ~30 s.
2. Connect the PC to the brick's WiFi.
3. Double-click `HARDWARE_CHECK.bat` in the project folder.
