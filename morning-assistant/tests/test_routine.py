import unittest
from datetime import datetime, timedelta

from morning_assistant.routine import Routine, Settings


class RoutineTest(unittest.TestCase):
    def setUp(self):
        self.steps = []
        self.r = Routine(Settings(), lambda name, **info: self.steps.append((name, info)))
        self.now = datetime(2026, 11, 18, 7, 0, 0)

    def later(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.r.tick(self.now)
        return self.now

    def wake(self):
        for _ in range(3):
            self.r.motion(self.later(5))

    def names(self):
        return [name for name, _ in self.steps]

    def test_full_morning(self):
        self.wake()
        self.assertEqual(self.names(), ["wake"])
        self.later(300)
        self.assertEqual(self.r.state, "shower")
        self.r.motion(self.later(600))
        self.assertEqual(self.names(), ["wake", "back"])
        self.r.door_opened(self.later(900))
        self.assertEqual(self.steps[-1], ("leaving", {"items": "keys, car key, phone and laptop"}))
        self.later(121)
        self.assertEqual(self.r.state, "away")
        self.assertEqual(self.names(), ["wake", "back", "leaving"])

    def test_single_motion_or_outside_window_does_not_wake(self):
        self.r.motion(self.now)
        self.r.motion(self.later(120))
        self.assertEqual(self.r.state, "idle")
        self.now = datetime(2026, 11, 18, 23, 0, 0)
        self.wake()
        self.assertEqual(self.steps, [])

    def test_wake_only_once_a_day(self):
        self.wake()
        self.r.door_opened(self.later(10))
        self.later(121)
        self.r.door_opened(self.later(60))   # came back home
        self.assertEqual(self.r.state, "idle")
        self.wake()
        self.assertEqual(self.names().count("wake"), 1)
        self.now += timedelta(days=1)
        self.wake()
        self.assertEqual(self.names().count("wake"), 2)

    def test_door_false_alarm_returns_to_previous_state(self):
        self.wake()
        self.r.door_opened(self.later(10))
        self.r.motion(self.later(10))        # within grace: still leaving
        self.assertEqual(self.r.state, "leaving")
        self.r.motion(self.later(40))        # still moving around at home
        self.assertEqual(self.r.state, "awake")

    def test_false_alarm_during_shower_counts_as_back(self):
        self.wake()
        self.later(300)
        self.r.door_opened(self.later(1))
        self.r.motion(self.later(60))
        self.assertEqual(self.r.state, "ready")
        self.assertEqual(self.names()[-1], "back")

    def test_forgotten_items(self):
        self.r.door_opened(self.now)
        self.r.tag_seen("laptop", self.later(10))    # stale by the time we check
        self.r.tag_seen("keys", self.later(100))
        self.later(20)
        self.assertEqual(self.steps[-1], ("forgotten", {"items": "keys"}))


if __name__ == "__main__":
    unittest.main()
