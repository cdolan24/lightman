# test_override_control.py

import time
import unittest

import pytest

from tune_management.override_control import OverrideControl, attach_gpio
from tune_management.profiles import ProfileManager
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher

gpiozero_mock = pytest.importorskip('gpiozero.pins.mock')

def wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False

class OverrideTest(unittest.TestCase):
    def setUp(self):
        tm = TuneManager(1)
        self.race = tm.save_tune("Race", b"r")
        self.street = tm.save_tune("Street", b"s")
        self.stock = tm.save_stock_tune(b"stock")
        ProfileManager(1).assign('race', self.race)
        ProfileManager(1).assign('street', self.street)
        self.switcher = TuneSwitcher(1)
        self.control = OverrideControl(self.switcher)

    def profile(self):
        return self.switcher.active()['profile']

class TestOverrideLogic(OverrideTest):
    def test_short_press_toggles_toward_street_by_default(self):
        self.control.short_press()                 # nothing active -> street
        self.assertEqual(self.profile(), 'street')
        self.control.short_press()                 # street -> race
        self.assertEqual(self.profile(), 'race')
        self.control.short_press()                 # race -> street
        self.assertEqual(self.profile(), 'street')

    def test_short_press_from_stock_goes_to_street(self):
        self.switcher.revert_to_stock('manual')
        self.control.short_press()
        self.assertEqual(self.profile(), 'street')

    def test_long_press_reverts_to_stock(self):
        self.switcher.switch('manual', profile='race')
        self.control.long_press()
        self.assertEqual(self.switcher.active()['tune_id'], self.stock)

    def test_switch_position(self):
        self.control.set_switch(True)
        self.assertEqual(self.profile(), 'race')
        self.control.set_switch(False)
        self.assertEqual(self.profile(), 'street')

    def test_refusal_recorded_as_manual(self):
        ProfileManager(2).assign('street', TuneManager(2).save_tune("Street", b"s"))
        switcher = TuneSwitcher(2)
        switcher.switch('manual', profile='street')
        with self.assertLogs('tune_management.override_control', level='WARNING'):
            result = OverrideControl(switcher).short_press()   # street -> race, but race unassigned
        self.assertFalse(result.ok)
        entry = switcher.history()[0]
        self.assertEqual((entry['source'], entry['success'], entry['requested_profile']), ('manual', False, 'race'))

class TestGpioBinding(OverrideTest):
    def setUp(self):
        super().setUp()
        self.factory = gpiozero_mock.MockFactory()
        self.addCleanup(self.factory.close)
        self.pin = self.factory.pin(17)

    def test_button_short_and_long_press(self):
        device = attach_gpio(self.control, 17, 'button', long_press=0.2, pin_factory=self.factory)
        self.addCleanup(device.close)
        self.pin.drive_low(); time.sleep(0.06); self.pin.drive_high()          # short press (pull-up: low = pressed)
        self.assertTrue(wait_for(lambda: self.profile() == 'street'))
        self.pin.drive_low()
        self.assertTrue(wait_for(lambda: self.switcher.active()['tune_id'] == self.stock))  # held -> stock
        self.pin.drive_high()
        time.sleep(0.1)
        self.assertEqual(self.switcher.active()['tune_id'], self.stock)      # release after hold: no toggle
        self.assertEqual([h['kind'] for h in self.switcher.history()], ['revert', 'switch'])

    def test_switch_mode_applies_startup_position_and_changes(self):
        self.pin.drive_high()                                                  # off at startup
        device = attach_gpio(self.control, 17, 'switch', pin_factory=self.factory)
        self.addCleanup(device.close)
        self.assertEqual(self.profile(), 'street')
        self.pin.drive_low()
        self.assertTrue(wait_for(lambda: self.profile() == 'race'))
        time.sleep(0.15)                                                       # past the bounce window
        self.pin.drive_high()
        self.assertTrue(wait_for(lambda: self.profile() == 'street'))

    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            attach_gpio(self.control, 17, 'dial', pin_factory=self.factory)

if __name__ == "__main__":
    unittest.main()
