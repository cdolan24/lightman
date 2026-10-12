# test_api.py

import unittest
from unittest import mock

from flask import Flask

from tune_management.tune_manager import TuneManager
from user_interface.api import api

def make_client():
    app = Flask(__name__)
    app.register_blueprint(api)
    return app.test_client()

class TestTuneAPI(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        tm = TuneManager(1)
        self.race = tm.save_tune("Race", b"r")
        self.street = tm.save_tune("Street", b"s")

    def test_assign_and_switch(self):
        r = self.client.put('/api/cars/1/profiles/Street', json={'tune_id': self.street})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['profile']['tune_name'], "Street")

        r = self.client.post('/api/cars/1/switch', json={'source': 'dashboard', 'profile': 'street'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json['ok'], r.json['active_tune_id'], r.json['method']), (True, self.street, 'software'))

        active = self.client.get('/api/cars/1/active').json
        self.assertEqual((active['tune_name'], active['profile']), ("Street", 'street'))
        (entry,) = self.client.get('/api/cars/1/history').json
        self.assertEqual((entry['source'], entry['success']), ('dashboard', True))

    def test_refused_switch_is_409(self):
        r = self.client.post('/api/cars/1/switch', json={'source': 'app', 'profile': 'race'})
        self.assertEqual(r.status_code, 409)
        self.assertFalse(r.json['ok'])
        self.assertIn("No tune is assigned", r.json['reason'])

    def test_unknown_profile_is_404(self):
        r = self.client.post('/api/cars/1/switch', json={'source': 'app', 'profile': 'qualifying'})
        self.assertEqual(r.status_code, 404)
        r = self.client.put('/api/cars/1/profiles/qualifying', json={'tune_id': self.race})
        self.assertEqual(r.status_code, 404)

    def test_bad_requests_are_400(self):
        for body in ({'profile': 'race'}, {'source': 'app'}, {'source': 'app', 'profile': 'race', 'tune_id': 1}):
            self.assertEqual(self.client.post('/api/cars/1/switch', json=body).status_code, 400)
        self.assertEqual(self.client.put('/api/cars/1/profiles/race', json={}).status_code, 400)

    def test_list_tunes_and_profiles(self):
        self.assertEqual([t['name'] for t in self.client.get('/api/cars/1/tunes').json], ["Race", "Street"])
        self.assertEqual([p['name'] for p in self.client.get('/api/cars/1/profiles').json], ['race', 'street'])

class TestApprovalAPI(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        self.tm = TuneManager(1)
        self.imported = self.tm.save_tune("Forum tune", b"?", origin='imported')

    def test_list_shows_origin_and_approval(self):
        (tune,) = self.client.get('/api/cars/1/tunes').json
        self.assertEqual((tune['origin'], tune['approved']), ('imported', False))

    def test_approve(self):
        r = self.client.post(f'/api/cars/1/tunes/{self.imported}/approve',
                             json={'source': 'dashboard', 'approved_by': 'Connor', 'note': 'looked fine'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json['tune']['approved'], r.json['tune']['approved_by']), (True, "Connor (dashboard)"))

    def test_auto_approval_refused(self):
        r = self.client.post(f'/api/cars/1/tunes/{self.imported}/approve',
                             json={'source': 'auto', 'approved_by': 'Lightman'})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(self.tm.get_tune(self.imported)['approved'])
        r = self.client.post(f'/api/cars/1/tunes/{self.imported}/approve', json={'source': 'app', 'approved_by': 5})
        self.assertEqual(r.status_code, 403)
        r = self.client.post('/api/cars/1/tunes/999/approve', json={'source': 'app', 'approved_by': 'Connor'})
        self.assertEqual(r.status_code, 404)

    def test_assigning_unapproved_is_409(self):
        r = self.client.put('/api/cars/1/profiles/race', json={'tune_id': self.imported})
        self.assertEqual(r.status_code, 409)

    def test_revert(self):
        self.assertEqual(self.client.post('/api/cars/1/revert', json={'source': 'app'}).status_code, 409)
        stock = self.tm.save_stock_tune(b"factory")
        r = self.client.post('/api/cars/1/revert', json={'source': 'app'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['active_tune_id'], stock)
        self.assertEqual(self.client.post('/api/cars/1/revert', json={}).status_code, 400)

class TestDashboardImport(unittest.TestCase):
    def test_import_does_not_touch_obd(self):
        with mock.patch('data_acquisition.obd_reader.obd.OBD') as obd_ctor:
            import importlib
            import user_interface.dashboard as dashboard
            importlib.reload(dashboard)
        obd_ctor.assert_not_called()
        self.assertIn('tune_api.switch', dashboard.app.view_functions)

if __name__ == "__main__":
    unittest.main()
