"""
Arduino droplet dispenser driver - Python equivalent of commDropplet.m.

The firmware (Droplet_Dispenser_V05.ino) is not modified; this module
speaks the same wire protocol.

    commDropplet('open', port)           -> Dispenser(port).open()
    commDropplet('ResetTime')            -> reset_time()
    commDropplet('ParDropSize', 120)     -> set_param('ParDropSize', 120)
    commDropplet('AudioDelayDrop', n)    -> audio_delay_drop()
    commDropplet('getEvents')            -> get_events()
    commDropplet('getEventsHistory')     -> get_events_history()
"""
import threading
import time

from . import proto

try:
    import serial
    from serial.tools import list_ports
    HAVE_SERIAL = True
except Exception:
    HAVE_SERIAL = False


def list_ports_available():
    if not HAVE_SERIAL:
        return []
    return [(p.device, f"{p.device} - {p.description}") for p in list_ports.comports()]


class Dispenser:
    """One Arduino UNO running Droplet_Dispenser_V05."""

    def __init__(self, port, baud=proto.BAUD):
        self.port, self.baud = port, baud
        self.ser = None
        self._buf = b""
        self._new = []          # received since the last get_events()
        self._hist = []         # everything since the last reset_time()
        # commDropplet.m caps the history at 10000 events and silently drops
        # the rest (SizeBufferEvents). There is no cap here.
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.params = {}

    # ---------------- connection ----------------
    def open(self):
        if not HAVE_SERIAL:
            raise RuntimeError("pyserial is not installed: pip install pyserial")
        self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(2.0)                      # Arduino resets when the port opens
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass
        self._buf = b""
        self._new.clear()
        self._hist.clear()
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    @property
    def connected(self):
        return self.ser is not None and self.ser.is_open

    # ---------------- event reading ----------------
    def _reader(self):
        while not self._stop.is_set():
            try:
                chunk = self.ser.read(256)
                if chunk:
                    with self._lock:
                        self._buf += chunk
                        evs, self._buf = proto.decode_events(self._buf)
                        if evs:
                            self._new.extend(evs)
                            self._hist.extend(evs)
                else:
                    time.sleep(0.002)
            except Exception:
                time.sleep(0.1)

    def get_events(self):
        """commDropplet('getEvents') - return new events and clear the queue."""
        with self._lock:
            out, self._new = self._new, []
        return out

    def get_events_history(self):
        """commDropplet('getEventsHistory') - everything since ResetTime."""
        with self._lock:
            return list(self._hist)

    # ---------------- commands ----------------
    def _send(self, name, arg=0):
        if not self.ser:
            raise RuntimeError("dispenser not connected")
        self.ser.write(proto.encode(name, arg))
        self.ser.flush()

    def reset_time(self):
        """commDropplet('ResetTime'): ResetCount + clear history.
        Like MATLAB, the serial input buffer is NOT flushed."""
        with self._lock:
            self._hist.clear()
            self._new.clear()
        self._send("ResetCount")

    def set_param(self, name, value):
        if name not in proto.PARAM_CMDS:
            raise KeyError(f"not a parameter command: {name}")
        self._send(name, value)
        self.params[name] = int(value)

    def apply_params(self, d):
        for k in proto.PARAM_CMDS:
            if k in d:
                self.set_param(k, d[k])
                time.sleep(0.02)

    def dropplet(self):            self._send("Dropplet")        # 1
    def flush(self, ms=None):                                     # 2 (ms)
        self._send("Flush", int(proto.FLUSH_DEFAULT_MS if ms is None else ms))
    def audio(self):               self._send("Audio")           # 10
    def audio_and_drop(self):      self._send("AudioAndDrop")    # 11
    def audio_delay_drop(self):    self._send("AudioDelayDrop")  # 13
