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
