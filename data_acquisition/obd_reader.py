# obd_reader.py

import threading

import obd

QUERIES = [
    ('rpm', obd.commands.RPM),
    ('speed', obd.commands.SPEED),
    ('throttle_pos', obd.commands.THROTTLE_POS),
    ('coolant_temp', obd.commands.COOLANT_TEMP),
    ('intake_temp', obd.commands.INTAKE_TEMP),
    ('fuel_level', obd.commands.FUEL_LEVEL),
]

class NullConnection:
    """Used when no adapter could be reached; every query is unavailable."""
    def query(self, cmd):
        return None

def connect(port=None, timeout=30.0):
    """Connect to the OBD-II adapter, giving up after timeout seconds.

    obd.OBD() can block indefinitely opening a Bluetooth serial port with nothing paired,
    so it runs in a daemon thread. Returns a NullConnection if the adapter isn't reachable.
    """
    result = []
    thread = threading.Thread(target=lambda: result.append(obd.OBD(port)), daemon=True)
    thread.start()
    thread.join(timeout)
    if result and result[0].is_connected():
        return result[0]
    return NullConnection()

class OBDReader:
    def __init__(self, connection=None):
        # Created lazily: connecting scans serial ports, which is slow and needs hardware.
        self._connection = connection

    @property
    def connection(self):
        if self._connection is None:
            self._connection = connect()  # auto-connects to USB or Bluetooth OBD-II
        return self._connection

    @property
    def is_connected(self):
        return not isinstance(self.connection, NullConnection)

    def get_basic_data(self):
        """Return each PID as a plain number in python-OBD's native unit, or None if unavailable."""
        data = {}
        for key, cmd in QUERIES:
            try:
                response = self.connection.query(cmd)
            except Exception:
                data[key] = None
                continue
            if response is None or response.is_null():
                data[key] = None
            else:
                value = response.value
                data[key] = float(getattr(value, 'magnitude', value))
        return data

if __name__ == "__main__":
    reader = OBDReader()
    print(reader.get_basic_data())
