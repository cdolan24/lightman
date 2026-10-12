# test_obd_reader.py

import threading
import unittest
from unittest import mock

import obd

from data_acquisition.obd_reader import NullConnection, OBDReader, connect

class FakeResponse:
    def __init__(self, value):
        self.value = value

    def is_null(self):
        return self.value is None

class FakeConnection:
    """Stands in for obd.OBD; values maps command -> reading (missing means null response)."""
    def __init__(self, values=None, raises=False):
        self.values = values or {}
        self.raises = raises

    def query(self, cmd):
        if self.raises:
            raise IOError("adapter unplugged")
        return FakeResponse(self.values.get(cmd))

class TestOBDReader(unittest.TestCase):
    def test_get_basic_data(self):
        conn = FakeConnection({
            obd.commands.RPM: obd.Unit.Quantity(3500, obd.Unit.rpm),
            obd.commands.SPEED: obd.Unit.Quantity(88, obd.Unit.kph),
        })
        data = OBDReader(connection=conn).get_basic_data()
        self.assertEqual(data['rpm'], 3500.0)
        self.assertEqual(data['speed'], 88.0)
        self.assertIsInstance(data['rpm'], float)

    def test_missing_pid_is_none(self):
        conn = FakeConnection({obd.commands.RPM: obd.Unit.Quantity(900, obd.Unit.rpm)})
        data = OBDReader(connection=conn).get_basic_data()
        self.assertEqual(data['rpm'], 900.0)
        self.assertIsNone(data['fuel_level'])
        self.assertEqual(set(data), {'rpm', 'speed', 'throttle_pos', 'coolant_temp', 'intake_temp', 'fuel_level'})

    def test_query_error_returns_none(self):
        data = OBDReader(connection=FakeConnection(raises=True)).get_basic_data()
        self.assertTrue(all(v is None for v in data.values()))

class TestConnect(unittest.TestCase):
    def test_hanging_adapter_times_out_to_null_connection(self):
        blocker = threading.Event()
        with mock.patch('data_acquisition.obd_reader.obd.OBD', side_effect=lambda port: blocker.wait()):
            conn = connect(timeout=0.1)
        blocker.set()
        self.assertIsInstance(conn, NullConnection)
        reader = OBDReader(connection=conn)
        self.assertFalse(reader.is_connected)
        self.assertTrue(all(v is None for v in reader.get_basic_data().values()))

    def test_unconnected_adapter_returns_null_connection(self):
        fake = mock.Mock(is_connected=mock.Mock(return_value=False))
        with mock.patch('data_acquisition.obd_reader.obd.OBD', return_value=fake):
            self.assertIsInstance(connect(timeout=1), NullConnection)

    def test_connected_adapter_is_returned(self):
        fake = mock.Mock(is_connected=mock.Mock(return_value=True))
        with mock.patch('data_acquisition.obd_reader.obd.OBD', return_value=fake):
            self.assertIs(connect('COM9', timeout=1), fake)

if __name__ == "__main__":
    unittest.main()
