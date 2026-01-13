# test_obd_reader.py

import unittest
from data_acquisition.obd_reader import OBDReader

class TestOBDReader(unittest.TestCase):
    def test_get_basic_data(self):
        reader = OBDReader()
        data = reader.get_basic_data()
        self.assertIsInstance(data, dict)
        self.assertIn('rpm', data)
        self.assertIn('speed', data)

if __name__ == "__main__":
    unittest.main()
