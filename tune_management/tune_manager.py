# tune_manager.py

import base64
import json
from datetime import datetime, timezone

from tune_management.car_database import connect_car_db

EXPORT_FORMAT = 'lightman-tune'
EXPORT_VERSION = 1

class TuneNotFound(LookupError):
    pass

class TuneInUse(ValueError):
    pass

class InvalidTuneFile(ValueError):
    pass

class TuneManager:
    def __init__(self, car_id):
        self.car_id = car_id
        connect_car_db(car_id).close()

    def _connect(self):
        return connect_car_db(self.car_id)

    def save_tune(self, name, data, notes=None):
        """Store a tune and return its id."""
        conn = self._connect()
        with conn:
            cur = conn.execute("INSERT INTO tunes (name, data, notes) VALUES (?, ?, ?)", (name, data, notes))
        conn.close()
        return cur.lastrowid

    def list_tunes(self):
        """Rows of (id, name, created_at) for tunes that haven't been deleted."""
        conn = self._connect()
        tunes = conn.execute("SELECT id, name, created_at FROM tunes WHERE deleted_at IS NULL ORDER BY id").fetchall()
        conn.close()
        return tunes

    def get_tune(self, tune_id):
        """Return the tune as a dict (id, name, data, notes, created_at); raise TuneNotFound if missing or deleted."""
        conn = self._connect()
        row = conn.execute("SELECT id, name, data, notes, created_at FROM tunes WHERE id = ? AND deleted_at IS NULL",
                           (tune_id,)).fetchone()
        conn.close()
        if row is None:
            raise TuneNotFound(f"Tune {tune_id} not found for car {self.car_id}")
        return dict(row)

    def rename_tune(self, tune_id, new_name):
        self.get_tune(tune_id)
        conn = self._connect()
        with conn:
            conn.execute("UPDATE tunes SET name = ? WHERE id = ?", (new_name, tune_id))
        conn.close()

    def delete_tune(self, tune_id):
        """Hide a tune from the library. Its row is kept so sessions and switch history still resolve it."""
        self.get_tune(tune_id)
        conn = self._connect()
        try:
            profiles = [r['name'] for r in conn.execute("SELECT name FROM profiles WHERE tune_id = ?", (tune_id,))]
            if profiles:
                raise TuneInUse(f"Tune {tune_id} is assigned to profile(s): {', '.join(profiles)}")
            if conn.execute("SELECT 1 FROM car_state WHERE active_tune_id = ?", (tune_id,)).fetchone():
                raise TuneInUse(f"Tune {tune_id} is the active tune")
            with conn:
                conn.execute("UPDATE tunes SET deleted_at = ? WHERE id = ?",
                             (datetime.now(timezone.utc).isoformat(), tune_id))
        finally:
            conn.close()

    def export_tune(self, tune_id, path):
        """Write the tune to a portable .lmtune file."""
        tune = self.get_tune(tune_id)
        payload = {
            'format': EXPORT_FORMAT,
            'version': EXPORT_VERSION,
            'name': tune['name'],
            'notes': tune['notes'],
            'data': base64.b64encode(tune['data']).decode('ascii'),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

    def import_tune(self, path):
        """Add a tune from a .lmtune file to this car's library and return its new id."""
        try:
            with open(path, encoding='utf-8') as f:
                payload = json.load(f)
            if payload.get('format') != EXPORT_FORMAT or payload.get('version') != EXPORT_VERSION:
                raise InvalidTuneFile(f"{path} is not a Lightman tune export")
            name = payload['name']
            data = base64.b64decode(payload['data'], validate=True)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            if isinstance(e, InvalidTuneFile):
                raise
            raise InvalidTuneFile(f"{path} is not a valid Lightman tune export: {e}") from e
        return self.save_tune(name, data, payload.get('notes'))

if __name__ == "__main__":
    tm = TuneManager(1)
    tm.save_tune("Race Mode", b"tune_binary_data")
    print("Tunes:", [tuple(t) for t in tm.list_tunes()])
