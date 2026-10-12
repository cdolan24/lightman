# test_feedback_monitor.py

import unittest

from tune_management.car_database import connect_car_db, utc_now
from tune_management.profiles import ProfileManager
from tune_management.recommender import Recommendation
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher
from voice_assistant.feedback_monitor import FeedbackMonitor, say_lap_time

class RecordingAnnouncer:
    def __init__(self):
        self.said = []

    def say(self, text, priority='info'):
        self.said.append((priority, text))

    def take(self):
        said, self.said = self.said, []
        return said

class FakeRecommender:
    def __init__(self):
        self.current = []

    def recommend(self):
        return list(self.current)

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

class MonitorTest(unittest.TestCase):
    def setUp(self):
        self.announcer = RecordingAnnouncer()
        self.recommender = FakeRecommender()
        self.clock = FakeClock()
        self.conn = connect_car_db(1)
        self.session = self.new_session()

    def tearDown(self):
        self.conn.close()

    def monitor(self, **limits):
        return FeedbackMonitor(1, self.announcer, limits, self.recommender, self.clock)

    def new_session(self):
        with self.conn:
            return self.conn.execute("INSERT INTO sessions (started_at) VALUES (?)", (utc_now(),)).lastrowid

    def sample(self, rpm=3000.0, coolant=90.0, fuel=50.0):
        with self.conn:
            self.conn.execute("INSERT INTO samples (session_id, wall_time, elapsed, rpm, coolant_temp, fuel_level) "
                              "VALUES (?, ?, 0, ?, ?, ?)", (self.session, utc_now(), rpm, coolant, fuel))

    def lap(self, number, duration):
        with self.conn:
            self.conn.execute("INSERT INTO laps (session_id, lap_number, start_elapsed, end_elapsed, duration) "
                              "VALUES (?, ?, 0, ?, ?)", (self.session, number, duration, duration))

class TestEngineAlerts(MonitorTest):
    def test_coolant_alert_once_then_repeat_after_interval(self):
        m = self.monitor()
        self.sample(coolant=112)
        m.check()
        ((priority, text),) = self.announcer.take()
        self.assertEqual(priority, 'warning')
        self.assertIn("112 degrees", text)
        self.clock.now = 30
        self.sample(coolant=112)
        m.check()
        self.assertEqual(self.announcer.take(), [])
        self.clock.now = 61
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)

    def test_coolant_rearms_after_cooling(self):
        m = self.monitor()
        self.sample(coolant=111)
        m.check()
        self.sample(coolant=108)       # below limit but within 5 °C: still armed off
        m.check()
        self.sample(coolant=111)
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)
        self.sample(coolant=104)       # cooled 6 °C below: re-arms
        m.check()
        self.sample(coolant=111)
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)

    def test_lower_critical_limit(self):
        m = self.monitor(coolant_critical=100.0)
        self.sample(coolant=102)
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)

    def test_low_fuel_once_until_refuelled(self):
        m = self.monitor()
        for fuel in (8, 7, 6):
            self.sample(fuel=fuel)
            m.check()
        ((_, text),) = self.announcer.take()
        self.assertIn("Fuel is low, 8 percent", text)
        self.sample(fuel=80)
        m.check()
        self.sample(fuel=9)
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)

    def test_obd_loss_and_recovery(self):
        m = self.monitor()
        self.sample(rpm=3000)
        m.check()
        for _ in range(4):
            self.sample(rpm=None, coolant=None, fuel=None)
            m.check()
        self.assertEqual(self.announcer.take(), [])
        for _ in range(3):
            self.sample(rpm=None, coolant=None, fuel=None)
            m.check()
        self.assertEqual(self.announcer.take(), [('warning', "Warning: lost engine data from the OBD adapter.")])
        self.sample(rpm=2500)
        m.check()
        self.assertEqual(self.announcer.take(), [('info', "Engine data is back.")])

    def test_no_engine_data_ever_is_not_a_loss(self):
        m = self.monitor()
        for _ in range(6):
            self.sample(rpm=None, coolant=None, fuel=None)
            m.check()
        self.assertEqual(self.announcer.take(), [])

    def test_ended_session_is_ignored(self):
        m = self.monitor()
        self.sample(coolant=115)
        with self.conn:
            self.conn.execute("UPDATE sessions SET ended_at = ?", (utc_now(),))
        m.check()
        self.assertEqual(self.announcer.take(), [])

class TestLaps(MonitorTest):
    def test_lap_wording(self):
        self.assertEqual(say_lap_time(92.4), "1 minute 32.4 seconds")
        self.assertEqual(say_lap_time(32.44), "32.4 seconds")
        self.assertEqual(say_lap_time(125.0), "2 minutes 5.0 seconds")

    def test_best_lap(self):
        m = self.monitor()
        self.lap(1, 95.0)
        m.check()
        self.lap(2, 92.4)
        m.check()
        self.lap(3, 93.0)
        m.check()
        self.assertEqual([t for _, t in self.announcer.take()], [
            "Lap 1, 1 minute 35.0 seconds.",
            "Lap 2, 1 minute 32.4 seconds, best lap.",
            "Lap 3, 1 minute 33.0 seconds.",
        ])

    def test_laps_before_start_not_announced(self):
        self.lap(1, 95.0)
        m = self.monitor()
        m.check()
        self.assertEqual(self.announcer.take(), [])

class TestRecommendationsAndSwitches(MonitorTest):
    def test_recommendation_announced_once(self):
        m = self.monitor()
        rec = Recommendation('race_overheating', 'warning', 'street', "Coolant is hot; switch to street.")
        self.recommender.current = [rec]
        for _ in range(3):
            m.check()
        self.assertEqual(self.announcer.take(), [('warning', "Coolant is hot; switch to street.")])
        self.recommender.current = []
        m.check()
        self.recommender.current = [rec]
        m.check()
        self.assertEqual(len(self.announcer.take()), 1)

    def test_switch_announcements(self):
        tm = TuneManager(1)
        ProfileManager(1).assign('race', tm.save_tune("Race", b"r"))
        tm.save_stock_tune(b"stock")
        switcher = TuneSwitcher(1)
        switcher.switch('manual', profile='race')    # before the monitor started
        m = self.monitor()
        switcher.switch('dashboard', profile='Race')
        switcher.switch('voice', profile='race')
        switcher.switch('app', profile='street')
        switcher.revert_to_stock('auto')
        m.check()
        self.assertEqual(self.announcer.take(), [
            ('info', "Race profile selected. Software only; the ECU was not changed."),
            ('warning', "Tune switch refused: No tune is assigned to the street profile"),
            ('info', "Reverted to the stock tune. Software only; the ECU was not changed."),
        ])

if __name__ == "__main__":
    unittest.main()
