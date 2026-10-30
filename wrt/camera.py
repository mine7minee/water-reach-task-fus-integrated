"""
Camera shuttle driver - Python equivalent of commProtocol.m.
ASCII protocol, 9600 baud.

    commProtocol('tagImage')       -> tag_image()     'f' + posixtime + \\n
    commProtocol('start')          -> start()         'a' + posixtime + \\n
    commProtocol('stop')           -> stop()          'z'
    commProtocol('setName', s)     -> set_name(s)     'n' + s + \\n
    commProtocol('setIdn', s)      -> set_idn(s)      'i' + s + \\n
    commProtocol('mkdir', s)       -> mkdir(s)        'd' + s + \\n
    commProtocol('stim')           -> stim()          's'
"""
import time

try:
    import serial
    HAVE_SERIAL = True
except Exception:
    HAVE_SERIAL = False


def _posix_now():
    return f"{time.time():.6f}"


class Camera:
    def __init__(self, port, timeout=3, baud=9600):
        self.port, self.baud, self.timeout = port, baud, timeout
        self.ser = None

    def open(self):
        if not HAVE_SERIAL:
            raise RuntimeError("pyserial is not installed: pip install pyserial")
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(0.3)

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    @property
    def connected(self):
        return self.ser is not None and self.ser.is_open

    def _w(self, data):
        if not self.ser:
            raise RuntimeError("camera not connected")
        if isinstance(data, str):
            data = data.encode("ascii", "ignore")
        self.ser.write(data)
        self.ser.flush()

    def tag_image(self):      self._w("f" + _posix_now() + "\n")
    def start(self):          self._w("a" + _posix_now() + "\n")
    def stop(self):           self._w("z")
    def set_name(self, name): self._w("n" + str(name) + "\n")
    def set_idn(self, idn):   self._w("i" + str(idn) + "\n")
    def mkdir(self, folder):  self._w("d" + str(folder) + "\n")
    def stim(self):           self._w("s")
