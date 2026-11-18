"""Run with:  python3 -m morning_assistant --config config.toml"""
import argparse
import logging
import queue
import shutil
import subprocess
import tomllib
import urllib.request
from datetime import datetime, time

from . import sensors
from .routine import Routine, Settings

log = logging.getLogger("assistant")


def parse_time(text):
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def load_settings(cfg):
    wake, shower, leave, items = (cfg.get(k, {}) for k in ("wake", "shower", "leave", "items"))
    s = Settings()
    if "window_start" in wake:
        s.window_start = parse_time(wake["window_start"])
    if "window_end" in wake:
        s.window_end = parse_time(wake["window_end"])
    s.motion_count = wake.get("motion_count", s.motion_count)
    s.motion_window_s = wake.get("motion_window_s", s.motion_window_s)
    s.shower_absence_s = shower.get("absence_s", s.shower_absence_s)
    s.leave_grace_s = leave.get("grace_s", s.leave_grace_s)
    s.leave_confirm_s = leave.get("confirm_s", s.leave_confirm_s)
    s.tag_timeout_s = items.get("tag_timeout_s", s.tag_timeout_s)
    s.items = items.get("names", s.items)
    return s


class Outputs:
    """Turns a routine step into speech, smart-plug calls and phone notifications."""

    def __init__(self, cfg):
        self.steps = cfg.get("steps", {})
        self.speech_cmd = cfg.get("speech", {}).get("command", ["espeak-ng", "-s", "150"])
        self.notify_url = cfg.get("notify", {}).get("url", "")

    def run_step(self, name, **info):
        step = self.steps.get(name)
        if not step:
            log.info("step %s (nothing configured)", name)
            return
        text = step.get("say", "").format(**info)
        if text:
            self.say(text)
        for url in step.get("http_get", []):
            self.http(url)
        if step.get("notify") and self.notify_url and text:
            self.http(self.notify_url, data=text.encode())

    def say(self, text):
        log.info("SAY: %s", text)
        if self.speech_cmd and shutil.which(self.speech_cmd[0]):
            try:
                subprocess.run([*self.speech_cmd, text], timeout=60)
            except (OSError, subprocess.SubprocessError) as exc:
                log.warning("speech failed: %s", exc)

    def http(self, url, data=None):
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=5).close()
            log.info("called %s", url)
        except OSError as exc:
            log.warning("request to %s failed: %s", url, exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    with open(args.config, "rb") as f:
        cfg = tomllib.load(f)

    outputs = Outputs(cfg)
    routine = Routine(load_settings(cfg), outputs.run_step)
    events = queue.Queue()

    gpio = cfg.get("gpio", {})
    devices = None
    if gpio.get("motion_pin") is not None or gpio.get("door_pin") is not None:
        try:
            devices = sensors.start_gpio(events, gpio.get("motion_pin"), gpio.get("door_pin"))
        except Exception as exc:  # not on a Pi, or wiring/driver problem
            log.warning("GPIO sensors unavailable: %s", exc)

    tags = cfg.get("items", {}).get("tags", {})
    if tags:
        try:
            sensors.start_ble(events, tags)
        except Exception as exc:
            log.warning("Bluetooth tag tracking unavailable: %s", exc)

    http = cfg.get("http", {})
    if http.get("port"):
        sensors.start_http(events, http.get("host", "127.0.0.1"), http["port"], lambda: routine.state)
        log.info("HTTP events on http://%s:%s", http.get("host", "127.0.0.1"), http["port"])

    log.info("running, state=%s", routine.state)
    state = routine.state
    while True:
        try:
            kind, value = events.get(timeout=1)
        except queue.Empty:
            kind = None
        now = datetime.now()
        if kind == "motion":
            routine.motion(now)
        elif kind == "door_opened":
            routine.door_opened(now)
        elif kind == "tag":
            routine.tag_seen(value, now)
        routine.tick(now)
        if routine.state != state:
            log.info("state %s -> %s", state, routine.state)
            state = routine.state


if __name__ == "__main__":
    main()
