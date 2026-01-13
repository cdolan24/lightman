# test_integration.py

import unittest
from integration_main import main

class TestIntegration(unittest.TestCase):
    def test_main_runs(self):
        try:
            main()
        except Exception as e:
            self.fail(f"Integration main raised an exception: {e}")

if __name__ == "__main__":
    unittest.main()
