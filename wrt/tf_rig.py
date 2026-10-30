"""
Tinkerforge rig driver (ESP32 Brick over WiFi).

Hardware used by the cue-reward task:
    Piezo Speaker Bricklet 2.0         -> beep at trial start
    Industrial Quad Relay Bricklet 2.1 -> blue LED, solenoid valve, green LED
    Multi Touch Bricklet 2.0           -> lick sensor (metal spout on electrode 0)

Nothing rig-specific is hard-coded:
  * host "auto" -> the PC's default gateway(s) are tried. When the PC is
    connected to the ESP32 Brick's own WiFi network, the gateway IS the brick.
  * empty UIDs   -> devices are found automatically by type (enumeration).
"""
import platform
import re
import subprocess
import threading
import time

try:
    from tinkerforge.ip_connection import IPConnection
    from tinkerforge.bricklet_piezo_speaker_v2 import BrickletPiezoSpeakerV2
    from tinkerforge.bricklet_industrial_quad_relay_v2 import BrickletIndustrialQuadRelayV2
    from tinkerforge.bricklet_multi_touch_v2 import BrickletMultiTouchV2
    HAVE_TINKERFORGE = True
except Exception:          # pragma: no cover
    HAVE_TINKERFORGE = False

DEV_PIEZO = 2145
DEV_RELAY = 2102
DEV_TOUCH = 2129
DEVICE_NAMES = {DEV_PIEZO: "Piezo Speaker Bricklet 2.0",
                DEV_RELAY: "Industrial Quad Relay Bricklet 2.1",
                DEV_TOUCH: "Multi Touch Bricklet 2.0"}

_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def detect_gateways():
    """Best-effort list of default-gateway IPv4 addresses (lowest metric first).
    Locale independent on Windows (parses 'route print')."""
    found = []
    try:
        system = platform.system()
        kw = {"capture_output": True, "text": True, "timeout": 5}
        if system == "Windows":
            kw["creationflags"] = 0x08000000      # CREATE_NO_WINDOW
            out = subprocess.run(["route", "print", "-4", "0.0.0.0"], **kw).stdout
            rows = []
            for line in out.splitlines():
                p = line.split()
                if len(p) >= 5 and p[0] == "0.0.0.0" and p[1] == "0.0.0.0" \
                        and _IPV4.match(p[2]):
                    try:
                        rows.append((int(p[-1]), p[2]))
                    except ValueError:
                        rows.append((9999, p[2]))
            found = [g for _, g in sorted(rows)]
        elif system == "Darwin":
            out = subprocess.run(["route", "-n", "get", "default"], **kw).stdout
            found = re.findall(r"gateway:\s*(\S+)", out)
        else:
            out = subprocess.run(["ip", "route"], **kw).stdout
            found = re.findall(r"default via (\S+)", out)
    except Exception:
        pass
    uniq = []
    for g in found:
        if g not in uniq and _IPV4.match(g):
            uniq.append(g)
    return uniq


class TinkerforgeRig:
    def __init__(self, tf_cfg, channels):
        if not HAVE_TINKERFORGE:
            raise RuntimeError("Tinkerforge library missing: pip install tinkerforge")
        self.cfg = dict(tf_cfg)
        self.ch = dict(channels)
        self.host = None
        self.port = int(self.cfg.get("port", 4223))
        self.ipcon = None
        self.piezo = self.relay = self.touch = None
        self.uids = {}
        self.found = {}                # uid -> (device_identifier, position)
        self._state = [False, False, False, False]
        self._lock = threading.Lock()
        self.lick_electrode = 0

    # ------------------------------------------------------------------
    # connection
    # ------------------------------------------------------------------
    def _candidates(self):
        h = str(self.cfg.get("host", "auto")).strip()
        if h and h.lower() != "auto":
            return [h]
        return detect_gateways() + ["localhost"]

    def _enumerate(self, wait=1.5):
        self.found = {}

        def cb(uid, connected_uid, position, hw, fw, dev_id, etype):
            if etype != IPConnection.ENUMERATION_TYPE_DISCONNECTED:
                self.found[uid] = (dev_id, position)

        self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, cb)
        self.ipcon.enumerate()
        t0 = time.time()
        while time.time() - t0 < wait:
            time.sleep(0.05)
        return self.found

    def _pick_uid(self, key, dev_id):
        manual = str(self.cfg.get(key, "")).strip()
        if manual:
            return manual
        for uid, (d, _) in self.found.items():
            if d == dev_id:
                return uid
        return ""

    def connect(self, log=print):
        last_err = None
        for host in self._candidates():
            ip = IPConnection()
            ip.set_timeout(2)
            try:
                log(f"Trying {host}:{self.port} ...")
                ip.connect(host, self.port)
            except Exception as e:
                last_err = e
                continue
            self.ipcon = ip
            self._enumerate()
            types = {d for d, _ in self.found.values()}
            if not ({DEV_PIEZO, DEV_RELAY, DEV_TOUCH} & types) and \
                    not any(self.cfg.get(k) for k in ("uid_piezo", "uid_relay", "uid_touch")):
                log(f"  {host}: connected but no rig Bricklets found.")
                try:
                    ip.disconnect()
                except Exception:
                    pass
                self.ipcon = None
                continue
            self.host = host
            break
        if self.ipcon is None:
            raise ConnectionError(
                "Could not reach the ESP32 Brick. Is the PC connected to the "
                "brick's WiFi network and is the 12 V supply on?"
                + (f"\nLast error: {last_err}" if last_err else ""))

        self.uids = {"piezo": self._pick_uid("uid_piezo", DEV_PIEZO),
                     "relay": self._pick_uid("uid_relay", DEV_RELAY),
                     "touch": self._pick_uid("uid_touch", DEV_TOUCH)}
        missing = [k for k, v in self.uids.items() if not v]
        if missing:
            self.close()
            raise RuntimeError("Bricklet(s) not found: " + ", ".join(missing)
                               + ". Check the Bricklet cables.")

        self.piezo = BrickletPiezoSpeakerV2(self.uids["piezo"], self.ipcon)
        self.relay = BrickletIndustrialQuadRelayV2(self.uids["relay"], self.ipcon)
        self.touch = BrickletMultiTouchV2(self.uids["touch"], self.ipcon)
        self.ipcon.set_auto_reconnect(True)
        self.configure_touch(0)
        self.all_off()
        log(f"Connected to rig at {self.host}.")
        return self.host

    def configure_touch(self, electrode=0):
        """Enable only the lick electrode (proximity electrode off)."""
        self.lick_electrode = int(electrode)
        cfg = [False] * 13
        cfg[self.lick_electrode] = True
        self._retry(lambda: self.touch.set_electrode_config(cfg))

    @property
    def connected(self):
        return self.ipcon is not None and \
            self.ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED

    def close(self):
        try:
            if self.relay:
                self.relay.set_value([False] * 4)
        except Exception:
            pass
        try:
            if self.ipcon:
                self.ipcon.disconnect()
        except Exception:
            pass
        self.ipcon = None

    def device_summary(self):
        lines = []
        for uid, (dev, pos) in sorted(self.found.items(), key=lambda x: x[1][1]):
            lines.append(f"Port {pos}: {DEVICE_NAMES.get(dev, f'device {dev}')}  (UID {uid})")
        return lines

    # ------------------------------------------------------------------
    # robust calls (WiFi can drop for a moment; auto-reconnect is on)
    # ------------------------------------------------------------------
    def _retry(self, fn, tries=10, stop_event=None):
        err = None
        for _ in range(tries):
            if stop_event is not None and stop_event.is_set():
                break
            try:
                return fn()
            except Exception as e:
                err = e
                time.sleep(0.5)
        raise RuntimeError(f"Rig not responding: {err}")

    # ------------------------------------------------------------------
    # outputs
    # ------------------------------------------------------------------
    def set_outputs(self, blue=None, valve=None, green=None):
        """Change only the given outputs, keep the others."""
        with self._lock:
            for name, val in (("blue_led", blue), ("valve", valve), ("green_led", green)):
                if val is not None:
                    self._state[int(self.ch[name])] = bool(val)
            state = list(self._state)
        self._retry(lambda: self.relay.set_value(state))

    def all_off(self):
        with self._lock:
            self._state = [False, False, False, False]
        self._retry(lambda: self.relay.set_value([False] * 4))

    def beep(self, freq=1000, volume=5, duration_ms=500):
        try:
            self.piezo.set_beep(int(freq), int(volume), int(duration_ms))
        except Exception:
            pass                          # a missed beep must not abort a session

    def valve_pulse(self, seconds):
        self.set_outputs(valve=True)
        time.sleep(float(seconds))
        self.set_outputs(valve=False)

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def read_lick(self):
        try:
            return bool(self.touch.get_touch_state()[self.lick_electrode])
        except Exception:
            return False
