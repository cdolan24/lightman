# test_api.py

import unittest
from unittest import mock

from flask import Flask

from tune_management.car_database import connect_car_db, utc_now
from tune_management.test_recommender import setup_car
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher
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

class TestRecommendationsAPI(unittest.TestCase):
    def test_recommendations(self):
        client = make_client()
        self.assertEqual(client.get('/api/cars/1/recommendations').json, [])
        setup_car(1, 'race')
        conn = connect_car_db(1)
        with conn:
            session = conn.execute("INSERT INTO sessions (started_at) VALUES ('x')").lastrowid
            conn.execute("INSERT INTO samples (session_id, wall_time, elapsed, coolant_temp) VALUES (?, ?, 0, 110)",
                         (session, utc_now()))
        conn.close()
        (rec,) = client.get('/api/cars/1/recommendations').json
        self.assertEqual((rec['rule'], rec['suggested_profile']), ('race_overheating', 'street'))

class TestLiveAPI(unittest.TestCase):
    def test_no_session(self):
        self.assertEqual(make_client().get('/api/cars/1/live').json,
                         {'session': None, 'sample': None, 'laps': [], 'best_lap': None})

    def test_running_session(self):
        conn = connect_car_db(1)
        with conn:
            ended = conn.execute("INSERT INTO sessions (started_at, ended_at) VALUES ('a', 'b')").lastrowid
            session = conn.execute("INSERT INTO sessions (started_at) VALUES (?)", (utc_now(),)).lastrowid
            for rpm in (2000.0, 4500.0):
                conn.execute("INSERT INTO samples (session_id, wall_time, elapsed, rpm, lap_number) "
                             "VALUES (?, ?, 0, ?, 3)", (session, utc_now(), rpm))
            for number, duration in ((1, 95.0), (2, 92.4)):
                conn.execute("INSERT INTO laps (session_id, lap_number, start_elapsed, end_elapsed, duration) "
                             "VALUES (?, ?, 0, 0, ?)", (session, number, duration))
        conn.close()
        with mock.patch('data_acquisition.obd_reader.obd.OBD') as obd_ctor:
            live = make_client().get('/api/cars/1/live').json
        obd_ctor.assert_not_called()
        self.assertEqual(live['session']['id'], session)
        self.assertNotEqual(live['session']['id'], ended)
        self.assertEqual((live['sample']['rpm'], live['sample']['lap_number']), (4500.0, 3))
        self.assertLess(live['sample']['age_seconds'], 5)
        self.assertEqual([lap['duration'] for lap in live['laps']], [95.0, 92.4])
        self.assertEqual(live['best_lap'], 2)

class TestDashboardPage(unittest.TestCase):
    def setUp(self):
        import user_interface.dashboard as dashboard
        self.app = dashboard.app
        response = self.app.test_client().get('/?car=2')
        self.assertEqual(response.status_code, 200)
        self.html = response.get_data(as_text=True)
        response.close()

    def test_page_served(self):
        self.assertIn('<title>Lightman</title>', self.html)

    def test_no_external_resources(self):
        self.assertNotRegex(self.html, r'https?://')

    def test_api_paths_exist(self):
        import re
        rules = {str(r) for r in self.app.url_map.iter_rules()}
        paths = set(re.findall(r"getJSON\('(/[a-z]+)", self.html)) | set(re.findall(r"act\('(/[a-z]+)'", self.html))
        self.assertEqual(paths, {'/live', '/active', '/profiles', '/recommendations', '/history', '/switch', '/revert'})
        for path in paths:
            self.assertIn('/api/cars/<int:car_id>' + path, rules)

class TestReportsAPI(unittest.TestCase):
    def test_sessions_report_and_comparison(self):
        from tune_management.test_performance_report import TRACK_A, add_session
        race = TuneManager(1).save_tune("Race", b"r")
        sid = add_session(tune_id=race, line=TRACK_A, laps=[(95.0, race), (92.0, race)])
        client = make_client()
        (session,) = client.get('/api/cars/1/sessions').json
        self.assertEqual((session['id'], session['lap_count']), (sid, 2))
        report = client.get(f'/api/cars/1/sessions/{sid}/report').json
        self.assertEqual(report['best_lap']['duration'], 92.0)
        self.assertEqual(client.get('/api/cars/1/sessions/999/report').status_code, 404)
        (track,) = client.get('/api/cars/1/tune-comparison').json
        self.assertEqual((track['line'], track['tunes'][0]['best_lap']), (TRACK_A, 92.0))

class TestCreateApp(unittest.TestCase):
    def test_factory_app(self):
        from user_interface.dashboard import create_app
        calls = []
        def factory(car_id):
            calls.append(car_id)
            return TuneSwitcher(car_id)
        client = create_app(factory).test_client()
        page = client.get('/')
        self.assertIn('<title>Lightman</title>', page.get_data(as_text=True))
        page.close()
        self.assertEqual(client.get('/api/cars/3/active').status_code, 200)
        self.assertEqual(calls, [3])

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
