# test_tune_switcher.py

import unittest

from tune_management.ecu_backend import ECUBackend, ECUError
from tune_management.profiles import ProfileManager
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher

class FlashBackend(ECUBackend):
    method = 'flash'

    def __init__(self):
        self.applied = []

    def apply(self, tune):
        self.applied.append(tune['id'])

class BrokenBackend(ECUBackend):
    method = 'live'

    def apply(self, tune):
        raise ECUError("no response from ECU")

class TestTuneSwitcher(unittest.TestCase):
    def setUp(self):
        tm = TuneManager(1)
        self.race = tm.save_tune("Race", b"r")
        self.street = tm.save_tune("Street", b"s")
        ProfileManager(1).assign('race', self.race)

    def test_switch_to_profile_persists(self):
        result = TuneSwitcher(1).switch('voice', profile='Race')
        self.assertTrue(result.ok)
        self.assertEqual((result.active_tune_id, result.active_profile, result.method), (self.race, 'race', 'software'))
        # A fresh instance (e.g. after a restart) sees the same state.
        active = TuneSwitcher(1).active()
        self.assertEqual((active['tune_id'], active['tune_name'], active['profile']), (self.race, "Race", 'race'))

    def test_switch_to_tune_clears_profile(self):
        switcher = TuneSwitcher(1)
        switcher.switch('voice', profile='race')
        result = switcher.switch('app', tune_id=self.street)
        self.assertTrue(result.ok)
        self.assertEqual(result.previous_tune_id, self.race)
        self.assertEqual((switcher.active()['tune_id'], switcher.active()['profile']), (self.street, None))

    def test_profile_without_tune_is_refused(self):
        switcher = TuneSwitcher(1)
        switcher.switch('voice', profile='race')
        result = switcher.switch('dashboard', profile='street')
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'refused')
        self.assertIn("street", result.reason)
        self.assertEqual(switcher.active()['tune_id'], self.race)

    def test_unknown_profile_and_tune(self):
        switcher = TuneSwitcher(1)
        self.assertEqual(switcher.switch('voice', profile='qualifying').error, 'not_found')
        self.assertEqual(switcher.switch('voice', tune_id=999).error, 'not_found')

    def test_invalid_source_or_target(self):
        switcher = TuneSwitcher(1)
        with self.assertRaises(ValueError):
            switcher.switch('telepathy', profile='race')
        with self.assertRaises(ValueError):
            switcher.switch('voice')
        with self.assertRaises(ValueError):
            switcher.switch('voice', profile='race', tune_id=self.race)

    def test_backend_failure_leaves_state(self):
        result = TuneSwitcher(1, backend=BrokenBackend()).switch('manual', profile='race')
        self.assertFalse(result.ok)
        self.assertEqual((result.error, result.method), ('failed', 'live'))
        self.assertIn("no response from ECU", result.reason)
        self.assertIsNone(TuneSwitcher(1).active()['tune_id'])

    def test_flash_refused_while_engine_running(self):
        backend = FlashBackend()
        result = TuneSwitcher(1, backend=backend, engine_rpm=lambda: 850.0).switch('app', profile='race')
        self.assertEqual(result.error, 'refused')
        self.assertIn("Engine must be off", result.reason)
        self.assertEqual(backend.applied, [])

    def test_flash_refused_when_rpm_unknown(self):
        for rpm in (lambda: None, None):
            backend = FlashBackend()
            result = TuneSwitcher(1, backend=backend, engine_rpm=rpm).switch('app', profile='race')
            self.assertEqual(result.error, 'refused')
            self.assertEqual(backend.applied, [])

    def test_flash_with_engine_off(self):
        backend = FlashBackend()
        result = TuneSwitcher(1, backend=backend, engine_rpm=lambda: 0.0).switch('app', profile='race')
        self.assertTrue(result.ok)
        self.assertEqual((result.method, backend.applied), ('flash', [self.race]))

    def test_history_records_success_and_refusal(self):
        switcher = TuneSwitcher(1)
        switcher.switch('dashboard', profile='race')
        switcher.switch('voice', profile='street')
        refused, ok = switcher.history()
        self.assertEqual((ok['source'], ok['success'], ok['to_tune_id'], ok['method']),
                         ('dashboard', True, self.race, 'software'))
        self.assertEqual((refused['source'], refused['success'], refused['requested_profile']),
                         ('voice', False, 'street'))
        self.assertEqual(refused['from_tune_id'], self.race)
        self.assertIn("No tune is assigned", refused['reason'])

class TestSwitchSafety(unittest.TestCase):
    def setUp(self):
        self.tm = TuneManager(1)
        self.race = self.tm.save_tune("Race", b"r")
        self.street = self.tm.save_tune("Street", b"s")
        ProfileManager(1).assign('race', self.race)
        ProfileManager(1).assign('street', self.street)

    def test_unapproved_tune_is_refused(self):
        imported = self.tm.save_tune("From forum", b"?", origin='imported')
        switcher = TuneSwitcher(1)
        switcher.switch('manual', profile='race')
        result = switcher.switch('app', tune_id=imported)
        self.assertEqual(result.error, 'refused')
        self.assertIn("not approved", result.reason)
        self.assertEqual(switcher.active()['tune_id'], self.race)
        self.assertFalse(switcher.history()[0]['success'])

    def test_approved_import_can_be_activated(self):
        imported = self.tm.save_tune("From forum", b"?", origin='imported')
        self.tm.approve_tune(imported, "Connor", 'dashboard')
        self.assertTrue(TuneSwitcher(1).switch('app', tune_id=imported).ok)

    def test_auto_by_profile(self):
        result = TuneSwitcher(1).switch('auto', profile='street')
        self.assertTrue(result.ok)
        self.assertEqual(result.active_tune_id, self.street)

    def test_auto_by_tune_id_is_refused(self):
        switcher = TuneSwitcher(1)
        result = switcher.switch('auto', tune_id=self.street)
        self.assertEqual(result.error, 'refused')
        self.assertIn("may only select a profile", result.reason)
        self.assertIsNone(switcher.active()['tune_id'])
        entry = switcher.history()[0]
        self.assertEqual((entry['source'], entry['success'], entry['requested_tune_id']), ('auto', False, self.street))

    def test_revert_to_stock(self):
        stock = self.tm.save_stock_tune(b"factory")
        switcher = TuneSwitcher(1)
        switcher.switch('manual', profile='race')
        result = switcher.revert_to_stock('voice')
        self.assertTrue(result.ok)
        self.assertEqual((result.active_tune_id, result.active_profile, result.previous_tune_id),
                         (stock, None, self.race))
        self.assertEqual((switcher.active()['tune_id'], switcher.active()['profile']), (stock, None))
        entry = switcher.history()[0]
        self.assertEqual((entry['kind'], entry['source'], entry['success']), ('revert', 'voice', True))

    def test_revert_without_stock(self):
        switcher = TuneSwitcher(1)
        result = switcher.revert_to_stock('auto')
        self.assertEqual(result.error, 'refused')
        self.assertIn("no stock tune", result.reason)
        self.assertEqual(switcher.history()[0]['kind'], 'revert')

    def test_revert_flash_while_running_is_refused(self):
        self.tm.save_stock_tune(b"factory")
        backend = FlashBackend()
        result = TuneSwitcher(1, backend=backend, engine_rpm=lambda: 3000.0).revert_to_stock('voice')
        self.assertEqual(result.error, 'refused')
        self.assertIn("Engine must be off", result.reason)
        self.assertEqual(backend.applied, [])

if __name__ == "__main__":
    unittest.main()
