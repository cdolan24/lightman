# test_tune_manager.py

import unittest
from tune_management.tune_manager import TuneManager

class TestTuneManager(unittest.TestCase):
    def test_save_and_list_tune(self):
        tm = TuneManager(99)  # Use a test car ID
        tm.save_tune("Test Tune", b"test_data")
        tunes = tm.list_tunes()
        self.assertTrue(any(t[1] == "Test Tune" for t in tunes))

if __name__ == "__main__":
    unittest.main()
