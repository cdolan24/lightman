# test_gps_reader.py

import io
import unittest
from datetime import datetime, timezone

from data_acquisition.gps_reader import GPSReader, parse_rmc

def nmea(body):
    """Wrap a sentence body with $ and a valid checksum."""
    checksum = 0
    for ch in body:
        checksum ^= ord(ch)
    return f"${body}*{checksum:02X}"

VALID = nmea("GPRMC,123519.50,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W")

class TestParseRMC(unittest.TestCase):
    def test_valid_fix(self):
        fix = parse_rmc(VALID)
        self.assertAlmostEqual(fix.latitude, 48 + 7.038 / 60)
        self.assertAlmostEqual(fix.longitude, 11 + 31.0 / 60)
        self.assertAlmostEqual(fix.speed, 22.4 * 1.852)
        expected = datetime(1994, 3, 23, 12, 35, 19, tzinfo=timezone.utc).timestamp() + 0.5
        self.assertAlmostEqual(fix.time, expected)

    def test_south_west_and_gn_talker(self):
        fix = parse_rmc(nmea("GNRMC,000001,A,3352.000,S,15112.000,W,0.0,0.0,010125,,"))
        self.assertAlmostEqual(fix.latitude, -(33 + 52 / 60))
        self.assertAlmostEqual(fix.longitude, -(151 + 12 / 60))

    def test_void_fix(self):
        self.assertIsNone(parse_rmc(nmea("GPRMC,123519,V,,,,,,,230394,,")))

    def test_bad_checksum(self):
        self.assertIsNone(parse_rmc(VALID[:-2] + "00"))

    def test_non_rmc(self):
        self.assertIsNone(parse_rmc(nmea("GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,")))

class TestGPSReader(unittest.TestCase):
    def test_poll_returns_new_fixes_and_keeps_latest(self):
        stream = io.BytesIO((VALID + "\r\n" + VALID[:-2] + "00\r\n").encode())
        gps = GPSReader(stream)
        fixes = gps.poll()
        self.assertEqual(len(fixes), 1)
        self.assertEqual(gps.latest_fix, fixes[0])
        self.assertEqual(gps.poll(), [])
        self.assertEqual(gps.latest_fix, fixes[0])

    def test_partial_line_is_buffered(self):
        stream = io.BytesIO()
        gps = GPSReader(stream)
        stream.write(VALID[:20].encode()); stream.seek(0)
        self.assertEqual(gps.poll(), [])
        stream.seek(0); stream.truncate()
        stream.write((VALID[20:] + "\r\n").encode()); stream.seek(0)
        self.assertEqual(len(gps.poll()), 1)

if __name__ == "__main__":
    unittest.main()
