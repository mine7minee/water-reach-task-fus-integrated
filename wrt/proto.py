"""
Arduino droplet dispenser - wire protocol.

SOURCE:       Droplet_Dispenser_V05.ino   (firmware - NOT modified)
VERIFIED VS.: commDropplet.m              (command codes and writeRegNum)

commDropplet.m writeRegNum:
    fwrite(port, uint8(command))          -> 1 byte
    fwrite(port, int16(val), 'int16')     -> 2 bytes, little-endian
commDropplet.m formatEvents:
    nEvents = floor(BytesAvailable/5)
    fread(port,1,'uint8') + fread(port,1,'uint32')

SENDING (read order inside the firmware loop()):
    if (Serial.available() >= 3)
        readBytes(&command, 1)     byte 1   = command code
        readBytes(&arg, 2)         byte 2,3 = int16 argument (little-endian)
  -> every command MUST be 3 bytes, even when the argument is unused.

EVENT REPORT (informEvent):
    byte 0    = event type
    byte 1..4 = millis() - timeOrig   (unsigned long, little-endian)
  -> every event is exactly 5 bytes.
"""
import struct

BAUD = 9600          # .ino setup(): Serial.begin(9600)

# Command codes (#define block at the top of the .ino)
CMD = {
    "Dropplet":          1,    # singledroppletmode()
    "Flush":             2,    # flushmode(arg)  -> arg = milliseconds
    "Audio":            10,    # AudioPlay()
    "AudioAndDrop":     11,    # droppletWithAudio()  (simultaneous)
    "ResetCount":       12,    # timeOrig = millis()
    "AudioDelayDrop":   13,    # AudioPlay(); delay(DelayAudioDrop); dropplet
    # parameter write commands
    "ParDropSize":       5,
    "ParAudioDuration":  7,
    "ParDelayAudioDrop": 8,
}

# MATLAB name -> firmware code  (commDropplet.m: 'ResetTime' -> ResetCount)
ALIAS = {"ResetTime": "ResetCount"}

# commDropplet.m says "arg = number of cycles" for Flush, but the firmware
# calls delay(time) inside flushmode -> the argument is MILLISECONDS.
FLUSH_DEFAULT_MS = 500

PARAM_CMDS = ("ParDropSize", "ParAudioDuration", "ParDelayAudioDrop")

# Event codes (informEvent calls in the .ino)
EVENT = {
     1: ("DROP_ON",       "Drop started"),
    10: ("DROP_OFF",      "Drop finished"),
     2: ("AUDIO_ON",      "Sound started"),
    20: ("AUDIO_OFF",     "Sound finished"),
     3: ("AUDIODROP_ON",  "Sound + drop started"),
    30: ("AUDIODROP_OFF", "Sound + drop finished"),
     4: ("TOUCH_ON",      "Touch started"),
    40: ("TOUCH_OFF",     "Touch finished"),
}
EVENT_SIZE = 5


def encode(name, arg=0):
    """Encode a command as 3 bytes. The firmware always reads 3 bytes."""
    name = ALIAS.get(name, name)
    if name not in CMD:
        raise KeyError(f"unknown command: {name}")
    a = int(arg)
    if not (-32768 <= a <= 32767):
        raise ValueError(f"argument outside int16 range: {a}")
    return struct.pack("<Bh", CMD[name], a)


def decode_events(buf):
    """Extract complete 5-byte event frames from a buffer.
    Returns (events, remaining_buffer);
    event = {"code": int, "name": str, "label": str, "ms": int}"""
    out, i, n = [], 0, len(buf)
    while n - i >= EVENT_SIZE:
        code = buf[i]
        ms = struct.unpack_from("<I", buf, i + 1)[0]
        name, label = EVENT.get(code, (f"UNKNOWN_{code}", f"unknown code {code}"))
        out.append({"code": code, "name": name, "label": label, "ms": ms})
        i += EVENT_SIZE
    return out, buf[i:]
