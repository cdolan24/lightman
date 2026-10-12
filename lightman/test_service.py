# test_service.py

import builtins
import json
import threading
import time
import unittest
import urllib.request
from unittest import mock

import obd

from data_acquisition.test_obd_reader import FakeConnection
from lightman.config import DEFAULTS, load_config
from lightman.service import LightmanService, supervise
from tune_management import car_database
from tune_management.car_database import connect_car_db
from tune_management.profiles import ProfileManager
from tune_management.tune_manager import TuneManager

def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False

def make_config(**sections):
    config = load_config(None)
    config['db_root'] = str(car_database.DB_ROOT)   # the per-test temp dir from conftest
    config['dashboard'] = {'host': '127.0.0.1', 'port': 0}
    config['logging']['rate'] = 10.0
    for name, values in sections.items():
        config[name].update(values)
    return config

def rows(sql):
    conn = connect_car_db(1)
    result = conn.execute(sql).fetchall()
    conn.close()
    return result

class TestService(unittest.TestCase):
    def start(self, config=None, **kwargs):
        self.spoken = []
        kwargs.setdefault('obd_connect', lambda port, timeout: FakeConnection(
            {obd.commands.RPM: obd.Unit.Quantity(2500, obd.Unit.rpm)}))
        kwargs.setdefault('make_speak', lambda: self.spoken.append)
        service = LightmanService(config or make_config(), restart_delay=0.1, feedback_interval=0.1, **kwargs)
        service.start()
        self.addCleanup(service.stop)
        return service

    def get(self, service, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{service.port}{path}", timeout=5) as response:
            return json.loads(response.read())

    def test_runs_logger_dashboard_and_voice(self):
        service = self.start()
        self.assertTrue(wait_for(lambda: len(rows("SELECT * FROM samples")) >= 3))
        live = self.get(service, '/api/cars/1/live')
        self.assertEqual(live['sample']['rpm'], 2500.0)
        self.assertTrue(wait_for(lambda: "Lightman copilot online." in self.spoken))

    def test_stop_closes_session(self):
        service = self.start()
        self.assertTrue(wait_for(lambda: rows("SELECT * FROM samples")))
        service.stop()
        (session,) = rows("SELECT * FROM sessions")
        self.assertIsNotNone(session['ended_at'])

    def test_engine_rpm_for_switching_comes_from_samples(self):
        service = self.start()
        self.assertTrue(wait_for(lambda: rows("SELECT * FROM samples")))
        from data_acquisition.data_logger import sampled_engine_rpm
        self.assertEqual(sampled_engine_rpm(1), 2500.0)

    def test_voice_failure_degrades(self):
        def broken():
            raise RuntimeError("no audio device")
        with self.assertLogs('lightman', level='ERROR') as logs:
            service = self.start(make_speak=broken)
        self.assertIsNone(service.announcer)
        self.assertIn("voice feedback disabled", "\n".join(logs.output))
        self.assertTrue(wait_for(lambda: rows("SELECT * FROM samples")))

    def test_gps_failure_degrades(self):
        def no_gps(port, baud):
            raise OSError(f"could not open {port}")
        config = make_config(gps={'port': '/dev/ttyACM9'}, lap_timing={'line': [40.0, -105.0, 40.0001, -105.0]})
        with self.assertLogs('lightman', level='ERROR') as logs:
            self.start(config, open_gps=no_gps)
            self.assertTrue(wait_for(lambda: rows("SELECT * FROM samples")))
        self.assertIn("GPS on /dev/ttyACM9 unavailable", "\n".join(logs.output))
        self.assertIsNone(rows("SELECT latitude FROM samples")[0]['latitude'])

    def test_no_obd_adapter_still_logs(self):
        from data_acquisition.obd_reader import NullConnection
        self.start(obd_connect=lambda port, timeout: NullConnection())
        self.assertTrue(wait_for(lambda: len(rows("SELECT * FROM samples")) >= 2))
        self.assertIsNone(rows("SELECT rpm FROM samples")[0]['rpm'])

    def test_stale_sessions_closed_on_start(self):
        conn = connect_car_db(1)
        with conn:
            conn.execute("INSERT INTO sessions (started_at) VALUES ('2026-10-11T10:00:00+00:00')")
        conn.close()
        self.start()
        first = rows("SELECT ended_at FROM sessions ORDER BY id")[0]
        self.assertEqual(first['ended_at'], '2026-10-11T10:00:00+00:00')

class TestOverrideInService(TestService):
    def test_default_has_no_override(self):
        self.assertIsNone(self.start().override_device)

    def test_configured_button(self):
        from gpiozero.pins.mock import MockFactory
        ProfileManager(1).assign('street', TuneManager(1).save_tune("Street", b"s"))
        factory = MockFactory()
        self.addCleanup(factory.close)
        service = self.start(make_config(override={'pin': 17}), gpio_pin_factory=factory)
        self.assertIsNotNone(service.override_device)
        pin = factory.pin(17)
        pin.drive_low(); time.sleep(0.06); pin.drive_high()      # short press
        self.assertTrue(wait_for(lambda: rows("SELECT active_profile FROM car_state")[0][0] == 'street'))

    def test_unavailable_gpio_degrades(self):
        real_import = builtins.__import__
        def no_gpiozero(name, *args, **kwargs):
            if name == 'gpiozero':
                raise ImportError("No module named 'gpiozero'")
            return real_import(name, *args, **kwargs)
        with mock.patch('builtins.__import__', no_gpiozero), self.assertLogs('lightman', level='ERROR') as logs:
            service = self.start(make_config(override={'pin': 17}))
        self.assertIsNone(service.override_device)
        self.assertIn("override disabled", "\n".join(logs.output))
        self.assertTrue(wait_for(lambda: rows("SELECT * FROM samples")))

class TestSupervise(unittest.TestCase):
    def test_restarts_crashing_component(self):
        stop, runs = threading.Event(), []
        def flaky():
            runs.append(1)
            if len(runs) < 3:
                raise RuntimeError("boom")
            stop.wait()
        thread = threading.Thread(target=supervise, args=('flaky', flaky, stop, 0.01))
        with self.assertLogs('lightman', level='ERROR'):
            thread.start()
            self.assertTrue(wait_for(lambda: len(runs) == 3))
        stop.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_other_components_keep_running(self):
        stop, healthy = threading.Event(), []
        def crashing():
            raise RuntimeError("always")
        def steady():
            while not stop.is_set():
                healthy.append(1)
                stop.wait(0.01)
        threads = [threading.Thread(target=supervise, args=(n, t, stop, 0.01))
                   for n, t in (('crashing', crashing), ('steady', steady))]
        with self.assertLogs('lightman', level='ERROR'):
            for t in threads:
                t.start()
            self.assertTrue(wait_for(lambda: len(healthy) > 20))
        stop.set()
        for t in threads:
            t.join(2)

if __name__ == "__main__":
    unittest.main()
