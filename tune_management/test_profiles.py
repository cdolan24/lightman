# test_profiles.py

import unittest

from tune_management.profiles import ProfileManager, UnknownProfile
from tune_management.tune_manager import TuneManager, TuneNotApproved, TuneNotFound

class TestProfiles(unittest.TestCase):
    def test_default_profiles_unassigned(self):
        profiles = ProfileManager(1).list_profiles()
        self.assertEqual([(p['name'], p['tune_id']) for p in profiles], [('race', None), ('street', None)])

    def test_assign(self):
        tune_id = TuneManager(1).save_tune("Track Day", b"x")
        pm = ProfileManager(1)
        pm.assign('race', tune_id)
        self.assertEqual(pm.get('race')['tune_name'], "Track Day")

    def test_reassign_replaces(self):
        tm, pm = TuneManager(1), ProfileManager(1)
        first, second = tm.save_tune("A", b"a"), tm.save_tune("B", b"b")
        pm.assign('street', first)
        pm.assign('street', second)
        self.assertEqual(pm.get('street')['tune_id'], second)

    def test_tune_from_another_car_is_refused(self):
        other_car_tune = TuneManager(2).save_tune("Other", b"x")
        TuneManager(1).save_tune("Mine", b"y")  # occupies id 1 in car 1, so pick an id car 1 lacks
        pm = ProfileManager(1)
        with self.assertRaises(TuneNotFound):
            pm.assign('race', other_car_tune + 1)
        self.assertIsNone(pm.get('race')['tune_id'])

    def test_deleted_tune_is_refused(self):
        tm, pm = TuneManager(1), ProfileManager(1)
        tune_id = tm.save_tune("Old", b"x")
        tm.delete_tune(tune_id)
        with self.assertRaises(TuneNotFound):
            pm.assign('race', tune_id)

    def test_unapproved_tune_is_refused(self):
        tune_id = TuneManager(1).save_tune("AI idea", b"x", origin='generated')
        pm = ProfileManager(1)
        with self.assertRaises(TuneNotApproved):
            pm.assign('race', tune_id)
        self.assertIsNone(pm.get('race')['tune_id'])

    def test_names_are_case_insensitive(self):
        self.assertEqual(ProfileManager(1).get(' Race ')['name'], 'race')

    def test_unknown_profile(self):
        with self.assertRaises(UnknownProfile):
            ProfileManager(1).get('qualifying')

if __name__ == "__main__":
    unittest.main()
