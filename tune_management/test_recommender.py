# test_recommender.py

import unittest
from datetime import datetime, timedelta, timezone

from tune_management.car_database import connect_car_db
from tune_management.profiles import ProfileManager
from tune_management.recommender import Recommender
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher

NOW = datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)

def setup_car(car_id, profile):
    tm = TuneManager(car_id)
    for name in ('race', 'street'):
        ProfileManager(car_id).assign(name, tm.save_tune(name.title(), name.encode()))
    TuneSwitcher(car_id).switch('manual', profile=profile)

def add_sample(car_id, age=1.0, coolant=90.0, intake=35.0, lap=None):
    conn = connect_car_db(car_id)
    with conn:
        session = conn.execute("INSERT INTO sessions (started_at) VALUES (?)", (NOW.isoformat(),)).lastrowid
        conn.execute("INSERT INTO samples (session_id, wall_time, elapsed, lap_number, coolant_temp, intake_temp) "
                     "VALUES (?, ?, 0, ?, ?, ?)",
                     (session, (NOW - timedelta(seconds=age)).isoformat(), lap, coolant, intake))
    conn.close()

def rules(car_id, **limits):
    return [(r.rule, r.severity, r.suggested_profile) for r in Recommender(car_id, limits, clock=lambda: NOW).recommend()]

class TestRecommender(unittest.TestCase):
    def test_overheating_on_race(self):
        setup_car(1, 'race')
        add_sample(1, coolant=112.0)
        (rec,) = Recommender(1, clock=lambda: NOW).recommend()
        self.assertEqual((rec.rule, rec.severity, rec.suggested_profile), ('race_overheating', 'warning', 'street'))
        self.assertIn("112", rec.reason)
        self.assertEqual(rec.values, {'coolant_temp': 112.0})

    def test_overheating_on_street_is_not_a_profile_change(self):
        setup_car(1, 'street')
        add_sample(1, coolant=108.0)
        self.assertEqual(rules(1), [])

    def test_heat_soak(self):
        setup_car(1, 'race')
        add_sample(1, intake=65.0)
        self.assertEqual(rules(1), [('race_heat_soak', 'warning', 'street')])

    def test_cold_engine(self):
        setup_car(1, 'race')
        add_sample(1, coolant=40.0)
        self.assertEqual(rules(1), [('race_cold_engine', 'info', 'street')])

    def test_track_on_street(self):
        setup_car(1, 'street')
        add_sample(1, lap=2)
        self.assertEqual(rules(1), [('track_on_street', 'info', 'race')])

    def test_track_on_street_but_hot_or_unknown(self):
        setup_car(1, 'street')
        add_sample(1, lap=2, coolant=108.0)
        self.assertEqual(rules(1), [])
        add_sample(1, lap=2, coolant=None)
        self.assertEqual(rules(1), [])

    def test_stale_or_missing_data(self):
        setup_car(1, 'race')
        self.assertEqual(rules(1), [])            # no session at all
        add_sample(1, age=60, coolant=112.0)
        self.assertEqual(rules(1), [])
        self.assertEqual(rules(1, max_sample_age=120), [('race_overheating', 'warning', 'street')])

    def test_null_reading_skips_rule(self):
        setup_car(1, 'race')
        add_sample(1, coolant=None, intake=None)
        self.assertEqual(rules(1), [])

    def test_configurable_limit(self):
        setup_car(1, 'race')
        add_sample(1, coolant=102.0)
        self.assertEqual(rules(1), [])
        self.assertEqual(rules(1, coolant_hot=100.0), [('race_overheating', 'warning', 'street')])

    def test_advisory_only(self):
        setup_car(1, 'race')
        add_sample(1, coolant=112.0, intake=70.0)
        switcher, tm = TuneSwitcher(1), TuneManager(1)
        before = (switcher.active(), switcher.history(), [tuple(t) for t in tm.list_tunes()],
                  ProfileManager(1).list_profiles())
        self.assertEqual(len(Recommender(1, clock=lambda: NOW).recommend()), 2)
        after = (switcher.active(), switcher.history(), [tuple(t) for t in tm.list_tunes()],
                 ProfileManager(1).list_profiles())
        self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()
