# lap_timer.py

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6371000.0

@dataclass
class Lap:
    lap_number: int
    start: float      # crossing times, in the same clock as the fixes fed to update()
    end: float

    @property
    def duration(self):
        return self.end - self.start

def _cross(ax, ay, bx, by):
    return ax * by - ay * bx

class LapTimer:
    """Times laps by detecting when the path between consecutive GPS fixes crosses a start/finish line."""

    def __init__(self, line, min_lap_time=10.0):
        (lat1, lon1), (lat2, lon2) = line
        self.min_lap_time = min_lap_time
        # Equirectangular projection around the line's midpoint; accurate over a few hundred metres.
        self._lat0 = (lat1 + lat2) / 2
        self._lon0 = (lon1 + lon2) / 2
        self._cos_lat0 = math.cos(math.radians(self._lat0))
        self._a = self._project(lat1, lon1)
        self._b = self._project(lat2, lon2)
        self._prev = None
        self._last_crossing = None
        self.current_lap = None

    def _project(self, lat, lon):
        x = math.radians(lon - self._lon0) * self._cos_lat0 * EARTH_RADIUS_M
        y = math.radians(lat - self._lat0) * EARTH_RADIUS_M
        return x, y

    def _crossing_time(self, t, point):
        """Interpolated time the segment prev->point crosses the line, or None."""
        if self._prev is None:
            return None
        t0, (px, py) = self._prev
        rx, ry = point[0] - px, point[1] - py
        sx, sy = self._b[0] - self._a[0], self._b[1] - self._a[1]
        denom = _cross(rx, ry, sx, sy)
        if denom == 0:
            return None
        qpx, qpy = self._a[0] - px, self._a[1] - py
        along_path = _cross(qpx, qpy, sx, sy) / denom
        along_line = _cross(qpx, qpy, rx, ry) / denom
        # Exclude the segment start so a fix landing exactly on the line counts once.
        if 0 < along_path <= 1 and 0 <= along_line <= 1:
            return t0 + along_path * (t - t0)
        return None

    def update(self, t, lat, lon):
        """Feed one fix. Return the Lap it completed, if any."""
        point = self._project(lat, lon)
        crossed_at = self._crossing_time(t, point)
        self._prev = (t, point)
        if crossed_at is None:
            return None
        if self._last_crossing is not None and crossed_at - self._last_crossing < self.min_lap_time:
            return None

        completed = None
        if self.current_lap is None:
            self.current_lap = 1
        else:
            completed = Lap(self.current_lap, self._last_crossing, crossed_at)
            self.current_lap += 1
        self._last_crossing = crossed_at
        return completed
