"""The routine as a state machine. No hardware and no clock in here:
sensors feed it events with a timestamp, and it calls `emit(step, **info)`.

    idle --motion burst in wake window--> awake   emits "wake"
    awake --no motion for a while-------> shower
    shower --motion---------------------> ready   emits "back"
    any (home) --door opens-------------> leaving emits "leaving"
    leaving --motion after grace--------> back to the previous state
    leaving --quiet until confirm-------> away    emits "forgotten" if tagged items stayed
    away --door opens-------------------> idle    emits "home"
"""
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta


@dataclass
class Settings:
    window_start: time = time(5, 30)
    window_end: time = time(10, 0)
    motion_count: int = 3          # this many motion events...
    motion_window_s: int = 60      # ...within this long means "woke up"
    shower_absence_s: int = 240    # no motion this long means "in the shower"
    leave_grace_s: int = 30        # motion this soon after the door is just you walking out
    leave_confirm_s: int = 120     # quiet this long after the door means "gone"
    tag_timeout_s: int = 45        # a tag heard this recently is still in the house
    items: list = field(default_factory=lambda: ["keys", "car key", "phone", "laptop"])


def join_words(words):
    words = list(words)
    if len(words) < 2:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


class Routine:
    def __init__(self, settings, emit):
        self.s = settings
        self.emit = emit
        self.state = "idle"
        self.prev_state = "idle"
        self.done_date = None      # the wake routine runs once per day
        self.recent_motion = []
        self.last_motion = None
        self.door_at = None
        self.tag_seen_at = {}

    def motion(self, now: datetime):
        self.last_motion = now
        if self.state == "leaving":
            if now - self.door_at < timedelta(seconds=self.s.leave_grace_s):
                return
            self.state = self.prev_state   # still moving around: false alarm
        if self.state == "idle":
            self._maybe_wake(now)
        elif self.state == "shower":
            self.state = "ready"
            self.emit("back")

    def _maybe_wake(self, now):
        if self.done_date == now.date():
            return
        if not (self.s.window_start <= now.time() <= self.s.window_end):
            return
        cutoff = now - timedelta(seconds=self.s.motion_window_s)
        self.recent_motion = [t for t in self.recent_motion if t >= cutoff] + [now]
        if len(self.recent_motion) >= self.s.motion_count:
            self.recent_motion = []
            self.done_date = now.date()
            self.state = "awake"
            self.emit("wake")

    def door_opened(self, now: datetime):
        if self.state == "away":
            self.state = "idle"
            self.emit("home")
        elif self.state != "leaving":
            self.prev_state = self.state
            self.state = "leaving"
            self.door_at = now
            self.emit("leaving", items=join_words(self.s.items))

    def tag_seen(self, item: str, now: datetime):
        self.tag_seen_at[item] = now

    def tick(self, now: datetime):
        if self.state == "awake":
            if now - self.last_motion >= timedelta(seconds=self.s.shower_absence_s):
                self.state = "shower"
        elif self.state == "leaving":
            if now - self.door_at >= timedelta(seconds=self.s.leave_confirm_s):
                self.state = "away"
                fresh = now - timedelta(seconds=self.s.tag_timeout_s)
                left = [i for i in self.s.items if self.tag_seen_at.get(i, datetime.min) >= fresh]
                if left:
                    self.emit("forgotten", items=join_words(left))
