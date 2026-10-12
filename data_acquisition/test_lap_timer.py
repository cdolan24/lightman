# test_lap_timer.py

import math
import unittest

from data_acquisition.lap_timer import LapTimer

LAT0, LON0 = 40.0, -105.0
M_PER_DEG_LAT = math.radians(1) * 6371000.0
M_PER_DEG_LON = M_PER_DEG_LAT * math.cos(math.radians(LAT0))

def pos(north_m, east_m):
    return LAT0 + north_m / M_PER_DEG_LAT, LON0 + east_m / M_PER_DEG_LON

# East-west line, 20 m wide, centred on the origin; the car drives north across it.
LINE = (pos(0, -10), pos(0, 10))

def cross_at(timer, t):
    """Drive from 10 m south to 10 m north of the line between t-0.5 and t+0.5,
    then loop back south around the east end of the line like a circuit would."""
    timer.update(t - 0.5, *pos(-10, 0))
    lap = timer.update(t + 0.5, *pos(10, 0))
    timer.update(t + 1.0, *pos(10, 30))
    timer.update(t + 1.5, *pos(-10, 30))
    return lap

class TestLapTimer(unittest.TestCase):
    def test_crossing_is_interpolated(self):
        timer = LapTimer(LINE)
        timer.update(0.0, *pos(-10, 0))
        timer.update(1.0, *pos(10, 0))
        self.assertEqual(timer.current_lap, 1)
        self.assertAlmostEqual(timer._last_crossing, 0.5, places=3)

    def test_path_beside_line_is_not_a_crossing(self):
        timer = LapTimer(LINE)
        timer.update(0.0, *pos(-10, 30))
        timer.update(1.0, *pos(10, 30))
        self.assertIsNone(timer.current_lap)

    def test_out_lap_has_no_lap_number(self):
        timer = LapTimer(LINE)
        timer.update(0.0, *pos(-50, 0))
        timer.update(1.0, *pos(-40, 0))
        self.assertIsNone(timer.current_lap)

    def test_two_completed_laps(self):
        timer = LapTimer(LINE)
        self.assertIsNone(cross_at(timer, 10))
        lap1 = cross_at(timer, 100)
        lap2 = cross_at(timer, 185)
        self.assertEqual((lap1.lap_number, round(lap1.duration, 3)), (1, 90))
        self.assertEqual((lap2.lap_number, round(lap2.duration, 3)), (2, 85))
        self.assertEqual(timer.current_lap, 3)

    def test_jitter_crossing_is_ignored(self):
        timer = LapTimer(LINE, min_lap_time=10)
        cross_at(timer, 10)
        self.assertIsNone(cross_at(timer, 12))
        self.assertEqual(timer.current_lap, 1)
        lap = cross_at(timer, 100)
        self.assertAlmostEqual(lap.duration, 90, places=3)

    def test_fix_exactly_on_line_counts_once(self):
        timer = LapTimer(LINE, min_lap_time=0)
        timer.update(0.0, *pos(-10, 0))
        timer.update(1.0, *pos(0, 0))
        timer.update(2.0, *pos(10, 0))
        self.assertEqual(timer.current_lap, 1)

if __name__ == "__main__":
    unittest.main()
