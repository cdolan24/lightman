# data_logger.py

import argparse
import time

from data_acquisition.lap_timer import LapTimer
from data_acquisition.obd_reader import OBDReader, QUERIES, connect
from tune_management.car_database import connect_car_db, get_db_path, utc_now

PID_FIELDS = [key for key, _ in QUERIES]
SAMPLE_FIELDS = ['session_id', 'wall_time', 'elapsed', 'lap_number', *PID_FIELDS,
                 'latitude', 'longitude', 'gps_speed']

class DataLogger:
    """Records a session of OBD-II + GPS samples, and laps, into a car's database."""

    def __init__(self, car_id, obd_reader, gps=None, lap_line=None, min_lap_time=10.0,
                 rate_hz=1.0, clock=time.monotonic, sleep=time.sleep, wall_clock=utc_now):
        self.car_id = car_id
        self.obd_reader = obd_reader
        self.gps = gps
        self.lap_line = lap_line
        self.min_lap_time = min_lap_time
        self.interval = 1.0 / rate_hz
        self.clock = clock
        self.sleep = sleep
        self.wall_clock = wall_clock
        self.session_id = None
        self.lap_timer = None
        self._conn = None

    def start(self, tune_id=None):
        """Open a session tagged with tune_id, or with the car's active tune when none is given."""
        self._conn = connect_car_db(self.car_id)
        if tune_id is None:
            tune_id = self._conn.execute("SELECT active_tune_id FROM car_state").fetchone()[0]
        cur = self._conn.execute(
            "INSERT INTO sessions (tune_id, started_at) VALUES (?, ?)", (tune_id, self.wall_clock()))
        self._conn.commit()
        self.session_id = cur.lastrowid
        self._started = self.clock()
        self._gps_offset = None  # session elapsed = gps time + offset
        self.lap_timer = LapTimer(self.lap_line, self.min_lap_time) if self.lap_line else None
        return self.session_id

    def tick(self):
        """Take one sample: drain GPS (feeding the lap timer), read OBD, store the row."""
        elapsed = self.clock() - self._started
        fixes = self.gps.poll() if self.gps else []
        if fixes and self._gps_offset is None:
            self._gps_offset = elapsed - fixes[-1].time
        if self.lap_timer:
            for fix in fixes:
                lap = self.lap_timer.update(fix.time, fix.latitude, fix.longitude)
                if lap:
                    self._conn.execute(
                        "INSERT INTO laps (session_id, lap_number, start_elapsed, end_elapsed, duration) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (self.session_id, lap.lap_number, lap.start + self._gps_offset,
                         lap.end + self._gps_offset, lap.duration))

        fix = self.gps.latest_fix if self.gps else None
        sample = {
            'session_id': self.session_id,
            'wall_time': self.wall_clock(),
            'elapsed': elapsed,
            'lap_number': self.lap_timer.current_lap if self.lap_timer else None,
            **self.obd_reader.get_basic_data(),
            'latitude': fix.latitude if fix else None,
            'longitude': fix.longitude if fix else None,
            'gps_speed': fix.speed if fix else None,
        }
        self._conn.execute(
            f"INSERT INTO samples ({', '.join(SAMPLE_FIELDS)}) VALUES ({', '.join('?' * len(SAMPLE_FIELDS))})",
            [sample[k] for k in SAMPLE_FIELDS])
        self._conn.commit()
        return sample

    def stop(self):
        self._conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (self.wall_clock(), self.session_id))
        self._conn.commit()
        self._conn.close()
        self._conn = None

    def run(self, tune_id=None, duration=None):
        """Sample at the configured rate until duration (seconds) elapses or Ctrl+C."""
        self.start(tune_id)
        next_tick = self.clock()
        try:
            while duration is None or self.clock() - self._started < duration:
                self.tick()
                next_tick += self.interval
                # When behind (slow adapter), run as fast as possible instead of sleeping.
                self.sleep(max(0.0, next_tick - self.clock()))
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
        return self.session_id

def _parse_line(text):
    lat1, lon1, lat2, lon2 = (float(v) for v in text.split(','))
    return (lat1, lon1), (lat2, lon2)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Log OBD-II and GPS data for a driving session.")
    parser.add_argument('--car-id', type=int, required=True, help="car whose database receives the session")
    parser.add_argument('--tune-id', type=int, help="tune to tag the session with (default: the car's active tune)")
    parser.add_argument('--rate', type=float, default=1.0, help="samples per second (default 1)")
    parser.add_argument('--duration', type=float, help="stop after this many seconds (default: until Ctrl+C)")
    parser.add_argument('--obd-port', help="OBD-II adapter port (default: auto-detect)")
    parser.add_argument('--obd-timeout', type=float, default=30.0,
                        help="seconds to wait for the OBD-II adapter before logging without it (default 30)")
    parser.add_argument('--gps-port', help="serial port of an NMEA GPS receiver, e.g. /dev/ttyACM0")
    parser.add_argument('--gps-baud', type=int, default=9600, help="GPS baud rate (default 9600)")
    parser.add_argument('--line', type=_parse_line, metavar='LAT1,LON1,LAT2,LON2',
                        help="start/finish line endpoints; enables lap timing (requires --gps-port)")
    parser.add_argument('--min-lap-time', type=float, default=10.0,
                        help="ignore line crossings closer together than this, in seconds (default 10)")
    args = parser.parse_args(argv)
    if args.line and not args.gps_port:
        parser.error("--line requires --gps-port")

    # Connect before opening the session so a slow adapter doesn't delay the first sample.
    reader = OBDReader(connect(args.obd_port, args.obd_timeout))
    if not reader.is_connected:
        print("OBD-II adapter not reachable; logging without engine data.")
    gps = None
    if args.gps_port:
        from data_acquisition.gps_reader import open_serial_gps
        gps = open_serial_gps(args.gps_port, args.gps_baud)

    logger = DataLogger(args.car_id, reader, gps=gps, lap_line=args.line,
                        min_lap_time=args.min_lap_time, rate_hz=args.rate)
    session_id = logger.run(tune_id=args.tune_id, duration=args.duration)
    print(f"Session {session_id} saved to {get_db_path(args.car_id)}")

if __name__ == "__main__":
    main()
