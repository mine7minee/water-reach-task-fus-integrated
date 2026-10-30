"""
Arduino dispenser training session - Python port of exp_Training.m.

exp_Training.m does not use the fUS scanner: its trial loop is
    for image = 1:nimag,  P.newImage(image);  pause(0.7);  end
so it can run in Python. (exp_Fus.m / exp_Dropplet.m use SCAN.doppler
and stay in MATLAB.)

Per trial:
    camera setName / setIdn
    dispenser ResetTime
    waitNoTuch(timeNoTuch)       animal must not touch for N seconds
    EventsBefore = history
    camera start ; dispenser ResetTime
    for image = 1..nimag: camera tagImage ; at Ndelivery -> AudioDelayDrop ; pause
    Events = history ; camera stop ; save
"""
import threading
import time
from datetime import datetime

from . import params as PR


def wait_no_touch(disp, time_no_touch, stop_event=None, on_reset=None, on_tick=None):
    """waitNoTuch.m: return once no event arrived for <time_no_touch> s.
    Returns (ok, n_resets, seconds_waited)."""
    t_begin = t0 = time.time()
    resets = 0
    while time.time() - t0 < time_no_touch:
        if stop_event is not None and stop_event.is_set():
            return False, resets, time.time() - t_begin
        events = disp.get_events()
        if events:
            t0 = time.time()
            resets += 1
            if on_reset:
                on_reset(events)
        if on_tick:
            on_tick(time.time() - t0, resets)
        time.sleep(0.01)
    return True, resets, time.time() - t_begin


class TrainingRunner:
    def __init__(self, disp, cam, recorder, emit, overrides=None):
        self.disp, self.cam, self.rec, self.emit = disp, cam, recorder, emit
        self.stop_event = threading.Event()
        self._thread = None
        self.completed_all = False
        v = PR.session_vars("TRAINING")
        p = PR.session_params("TRAINING")
        if overrides:
            v.update({k: val for k, val in overrides.items() if k in v})
            p.update({k: val for k, val in overrides.items() if k in p})
        self.v, self.p = v, p

    def _cam(self):
        return self.cam is not None and self.cam.connected

    def _new_image(self, image, itrial):
        """MultistimObject.newImage: tagImage; drop at Ndelivery."""
        if self._cam():
            self.cam.tag_image()
        self.emit("image", {"trial": itrial, "image": image, "nimag": self.v["nimag"]})
        if image == self.v["Ndelivery"]:
            self.disp.audio_delay_drop()
            self.emit("phase", {"text": "DROP DELIVERED (AudioDelayDrop)"})

    def start(self):
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.stop_event.set()

    def join(self, t=3.0):
        if self._thread:
            self._thread.join(timeout=t)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        try:
            self._loop()
        except Exception as e:
            self.emit("error", {"message": str(e)})
        finally:
            self.emit("finished", {"completed_all": self.completed_all})

    def _loop(self):
        v, p = self.v, self.p
        self.disp.apply_params(p)
        self.emit("log", {"text": f"Firmware parameters written: {p}"})
        if self._cam():
            self.cam.mkdir(self.rec.sub_folder)

        n = int(v["ntrials"])
        for itrial in range(1, n + 1):
            if self.stop_event.is_set():
                return
            if self._cam():
                self.cam.set_name(f"CAM_{itrial:02d}")
                self.cam.set_idn(f"{itrial:02d}")
            self.emit("trial_start", {"trial": itrial, "ntrials": n, "led": "-"})

            self.disp.reset_time()
            self.emit("phase", {"text": f"Waiting for {v['timeNoTuch']} s without touch"})
            ok, resets, waited = wait_no_touch(
                self.disp, v["timeNoTuch"], self.stop_event,
                on_tick=lambda el, r: self.emit(
                    "wait_tick", {"elapsed": el, "need": v["timeNoTuch"], "resets": r}))
            if not ok:
                return

            events_before = self.disp.get_events_history()
            if self._cam():
                self.cam.start()
            self.disp.reset_time()
            t_events0 = datetime.now()
            self.emit("phase", {"text": "Trial running"})

            pause = float(v["image_pause"])
            for image in range(1, int(v["nimag"]) + 1):
                if self.stop_event.is_set():
                    if self._cam():
                        self.cam.stop()
                    return
                self._new_image(image, itrial)
                t_end = time.time() + pause
                while time.time() < t_end and not self.stop_event.is_set():
                    time.sleep(0.005)

            self.disp.get_events()
            events = self.disp.get_events_history()
            if self._cam():
                self.cam.stop()
            row = self.rec.write_trial(itrial=itrial, events=events,
                                       events_before=events_before,
                                       t_events0=t_events0, vars_=v, params=p)
            self.emit("trial_end", {"trial": itrial, "row": row,
                                    "wait_resets": resets, "wait_seconds": waited})
        self.completed_all = True
