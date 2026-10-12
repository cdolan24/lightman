# test_data_logger.py

import sqlite3
import unittest

from data_acquisition.data_logger import DataLogger
from data_acquisition.gps_reader import GPSFix
from data_acquisition.test_lap_timer import LINE, pos
from data_acquisition.test_obd_reader import FakeConnection
from data_acquisition.obd_reader import OBDReader
from tune_management.car_database import get_db_path
from tune_management.profiles import ProfileManager
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

class FakeGPS:
    """Hands out one queued batch of fixes per poll()."""
    def __init__(self, batches):
        self.batches = list(batches)
        self.latest_fix = None

    def poll(self):
        fixes = self.batches.pop(0) if self.batches else []
        if fixes:
            self.latest_fix = fixes[-1]
        return fixes

class FixedReader:
    def __init__(self, data):
        self.data = data

    def get_basic_data(self):
        return dict(self.data)

READING = {'rpm': 3000.0, 'speed': 80.0, 'throttle_pos': 40.0,
           'coolant_temp': 90.0, 'intake_temp': 30.0, 'fuel_level': None}

def fix(t, north_m, east_m=0):
    lat, lon = pos(north_m, east_m)
    return GPSFix(time=1_700_000_000 + t, latitude=lat, longitude=lon, speed=100.0)

def query(car_id, sql):
    conn = sqlite3.connect(get_db_path(car_id))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows

class TestDataLogger(unittest.TestCase):
    def make_logger(self, car_id, reader=None, **kwargs):
        clock = FakeClock()
        logger = DataLogger(car_id, reader or FixedReader(READING), clock=clock, sleep=clock.sleep, **kwargs)
        return logger, clock

    def test_session_with_tune(self):
        tm = TuneManager(1)
        tm.save_tune("Street", b"x")
        tune_id = tm.list_tunes()[0][0]
        logger, _ = self.make_logger(1)
        session_id = logger.start(tune_id=tune_id)
        logger.tick()
        logger.stop()
        (session,) = query(1, "SELECT * FROM sessions")
        self.assertEqual((session['id'], session['tune_id']), (session_id, tune_id))
        self.assertIsNotNone(session['started_at'])
        self.assertIsNotNone(session['ended_at'])

    def test_session_without_tune(self):
        logger, _ = self.make_logger(2)
        logger.start()
        logger.stop()
        (session,) = query(2, "SELECT * FROM sessions")
        self.assertIsNone(session['tune_id'])

    def test_session_defaults_to_active_tune(self):
        race = TuneManager(11).save_tune("Race", b"r")
        ProfileManager(11).assign('race', race)
        TuneSwitcher(11).switch('manual', profile='race')
        logger, _ = self.make_logger(11)
        logger.start()
        logger.stop()
        (session,) = query(11, "SELECT * FROM sessions")
        self.assertEqual(session['tune_id'], race)

    def test_samples_at_rate(self):
        logger, _ = self.make_logger(3, rate_hz=2)
        logger.run(duration=5)
        samples = query(3, "SELECT * FROM samples ORDER BY id")
        self.assertEqual(len(samples), 10)
        self.assertEqual([s['elapsed'] for s in samples[:3]], [0.0, 0.5, 1.0])
        self.assertEqual(samples[0]['rpm'], 3000.0)
        self.assertIsNone(samples[0]['fuel_level'])
        # No GPS configured: position and lap are null.
        self.assertIsNone(samples[0]['latitude'])
        self.assertIsNone(samples[0]['lap_number'])

    def test_disconnected_adapter_still_logs(self):
        reader = OBDReader(connection=FakeConnection(raises=True))
        logger, _ = self.make_logger(4, reader=reader)
        logger.run(duration=3)
        samples = query(4, "SELECT * FROM samples")
        self.assertEqual(len(samples), 3)
        self.assertTrue(all(s['rpm'] is None for s in samples))

    def test_gps_position_and_no_fix(self):
        gps = FakeGPS([[], [fix(0, -50)]])
        logger, clock = self.make_logger(5, gps=gps)
        logger.start()
        first = logger.tick()
        clock.now += 1
        second = logger.tick()
        logger.stop()
        self.assertIsNone(first['latitude'])
        self.assertAlmostEqual(second['latitude'], pos(-50, 0)[0])
        self.assertEqual(second['gps_speed'], 100.0)

    def test_laps_recorded_and_samples_tagged(self):
        loop_back = lambda t: [fix(t + 1, 10, 30), fix(t + 1.5, -10, 30)]
        gps = FakeGPS([
            [fix(0, -50)],                                    # out-lap
            [fix(9.5, -10), fix(10.5, 10)] + loop_back(10),   # crossing at t=10 -> lap 1
            [fix(99.5, -10), fix(100.5, 10)] + loop_back(100),  # crossing at t=100 -> lap 2
        ])
        logger, clock = self.make_logger(6, gps=gps, lap_line=LINE)
        logger.start()
        lap_numbers = []
        for elapsed in (0, 12, 102):
            clock.now = elapsed
            lap_numbers.append(logger.tick()['lap_number'])
        logger.stop()
        self.assertEqual(lap_numbers, [None, 1, 2])
        (lap,) = query(6, "SELECT * FROM laps")
        self.assertEqual(lap['lap_number'], 1)
        self.assertAlmostEqual(lap['duration'], 90.0, places=3)
        # GPS time mapped onto session elapsed time via the first fix (t=0 at elapsed 0).
        self.assertAlmostEqual(lap['start_elapsed'], 10.0, places=3)
        self.assertAlmostEqual(lap['end_elapsed'], 100.0, places=3)

if __name__ == "__main__":
    unittest.main()
