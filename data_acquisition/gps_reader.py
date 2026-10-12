# gps_reader.py

from dataclasses import dataclass
from datetime import datetime, timezone

KNOTS_TO_KPH = 1.852

@dataclass
class GPSFix:
    time: float        # UTC epoch seconds reported by the receiver
    latitude: float
    longitude: float
    speed: float       # km/h

def _checksum_ok(sentence):
    if '*' not in sentence:
        return False
    body, checksum = sentence[1:].split('*', 1)
    calc = 0
    for ch in body:
        calc ^= ord(ch)
    try:
        return calc == int(checksum[:2], 16)
    except ValueError:
        return False

def _to_degrees(value, hemisphere):
    # NMEA packs coordinates as (d)ddmm.mmmm
    dot = value.index('.')
    degrees = int(value[:dot - 2]) + float(value[dot - 2:]) / 60
    return -degrees if hemisphere in ('S', 'W') else degrees

def parse_rmc(sentence):
    """Parse an NMEA RMC sentence from any talker. Return a GPSFix, or None if invalid or not RMC."""
    sentence = sentence.strip()
    if not sentence.startswith('$') or sentence[3:6] != 'RMC' or not _checksum_ok(sentence):
        return None
    fields = sentence.split('*')[0].split(',')
    try:
        _, hhmmss, status, lat, ns, lon, ew, knots, _course, ddmmyy = fields[:10]
        if status != 'A':
            return None
        stamp = datetime.strptime(ddmmyy + hhmmss.split('.')[0], '%d%m%y%H%M%S').replace(tzinfo=timezone.utc)
        fraction = float('0.' + hhmmss.split('.')[1]) if '.' in hhmmss else 0.0
        return GPSFix(
            time=stamp.timestamp() + fraction,
            latitude=_to_degrees(lat, ns),
            longitude=_to_degrees(lon, ew),
            speed=float(knots or 0) * KNOTS_TO_KPH,
        )
    except ValueError:
        return None

class GPSReader:
    """Reads NMEA from a non-blocking byte stream (e.g. a pyserial port opened with timeout=0)."""
    CHUNK = 4096

    def __init__(self, stream):
        self.stream = stream
        self.latest_fix = None
        self._buffer = ''

    def poll(self):
        """Drain whatever the receiver has sent and return the new valid fixes, oldest first."""
        while True:
            chunk = self.stream.read(self.CHUNK)
            if not chunk:
                break
            self._buffer += chunk.decode('ascii', errors='replace') if isinstance(chunk, bytes) else chunk
        *lines, self._buffer = self._buffer.split('\n')
        fixes = [fix for fix in map(parse_rmc, lines) if fix is not None]
        if fixes:
            self.latest_fix = fixes[-1]
        return fixes

def open_serial_gps(port, baudrate=9600):
    import serial
    return GPSReader(serial.Serial(port, baudrate=baudrate, timeout=0))

if __name__ == "__main__":
    import sys
    import time
    gps = open_serial_gps(sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0')
    while True:
        for fix in gps.poll():
            print(fix)
        time.sleep(0.2)
