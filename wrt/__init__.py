"""Water Reach Task - fUS integrated control software.

Two hardware back-ends share one interface:

* Tinkerforge rig  (ESP32 Brick over WiFi): cue LEDs, solenoid valve,
  piezo beep and capacitive lick sensor.
* Arduino droplet dispenser + camera shuttle (serial): Python port of the
  lab's MATLAB layer (commDropplet.m, commProtocol.m, exp_Training.m).
  The dispenser firmware (Droplet_Dispenser_V05.ino) is NOT modified.

Author: Meryem Mine Kurum
"""
__version__ = "1.0.0"
__author__ = "Meryem Mine Kurum"
