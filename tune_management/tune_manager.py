# tune_manager.py

import base64
import json
import sqlite3
from datetime import datetime, timezone

from tune_management.car_database import connect_car_db

EXPORT_FORMAT = 'lightman-tune'
EXPORT_VERSION = 1

ORIGINS = ('stock', 'human', 'imported', 'generated')
SELF_APPROVED_ORIGINS = ('stock', 'human')
# Tunes are approved by a person; voice (mishearing, passengers) and automation never qualify.
APPROVAL_SOURCES = ('dashboard', 'app', 'manual')
TUNE_COLUMNS = "id, name, data, notes, created_at, origin, approved_at, approved_by, approval_note"

class TuneNotFound(LookupError):
    pass

class TuneInUse(ValueError):
    pass

class InvalidTuneFile(ValueError):
    pass

class ApprovalRefused(ValueError):
    pass

class StockTuneExists(ValueError):
    pass

class TuneNotApproved(ValueError):
    pass

def _now():
    return datetime.now(timezone.utc).isoformat()

def _tune_dict(row):
    tune = dict(row)
    tune['approved'] = tune['approved_at'] is not None
    return tune

class TuneManager:
    def __init__(self, car_id):
        self.car_id = car_id
        connect_car_db(car_id).close()

    def _connect(self):
        return connect_car_db(self.car_id)

    def save_tune(self, name, data, notes=None, origin='human'):
        """Store a tune and return its id. Stock and human tunes are approved on save; others need approve_tune."""
        if origin not in ORIGINS:
            raise ValueError(f"origin must be one of {ORIGINS}, not {origin!r}")
        approved_at, approved_by = (_now(), 'self' if origin == 'human' else 'stock')             if origin in SELF_APPROVED_ORIGINS else (None, None)
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO tunes (name, data, notes, origin, approved_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, data, notes, origin, approved_at, approved_by))
        except sqlite3.IntegrityError as e:
            if origin == 'stock':
                raise StockTuneExists(f"Car {self.car_id} already has a stock tune") from e
            raise
        finally:
            conn.close()
        return cur.lastrowid

    def save_stock_tune(self, data, name="Stock", notes=None):
        """Store the car's one protected stock tune (refused if it already has one)."""
        return self.save_tune(name, data, notes, origin='stock')

    def get_stock_tune(self):
        """The stock tune as a dict, or None if the car doesn't have one."""
        conn = self._connect()
        row = conn.execute(f"SELECT {TUNE_COLUMNS} FROM tunes WHERE origin = 'stock'").fetchone()
        conn.close()
        return _tune_dict(row) if row else None

    def approve_tune(self, tune_id, approved_by, source, note=None):
        """Record a person's approval of a tune. Already-approved tunes keep their original approval."""
        if source not in APPROVAL_SOURCES:
            raise ApprovalRefused(f"Tunes can only be approved from {', '.join(APPROVAL_SOURCES)}, not {source!r}")
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ApprovalRefused("An approver name is required")
        tune = self.get_tune(tune_id)
        if tune['approved']:
            return tune
        conn = self._connect()
        with conn:
            conn.execute("UPDATE tunes SET approved_at = ?, approved_by = ?, approval_note = ? WHERE id = ?",
                         (_now(), f"{approved_by.strip()} ({source})", note, tune_id))
        conn.close()
        return self.get_tune(tune_id)

    def list_tunes(self):
        """Rows of (id, name, created_at, origin, approved_at, approved_by) for tunes that haven't been deleted."""
        conn = self._connect()
        tunes = conn.execute("SELECT id, name, created_at, origin, approved_at, approved_by FROM tunes "
                             "WHERE deleted_at IS NULL ORDER BY id").fetchall()
        conn.close()
        return tunes

    def get_tune(self, tune_id):
        """Return the tune as a dict (data, origin, approval fields, 'approved', ...); raise TuneNotFound if missing or deleted."""
        conn = self._connect()
        row = conn.execute(f"SELECT {TUNE_COLUMNS} FROM tunes WHERE id = ? AND deleted_at IS NULL",
                           (tune_id,)).fetchone()
        conn.close()
        if row is None:
            raise TuneNotFound(f"Tune {tune_id} not found for car {self.car_id}")
        return _tune_dict(row)

    def rename_tune(self, tune_id, new_name):
        self.get_tune(tune_id)
        conn = self._connect()
        with conn:
            conn.execute("UPDATE tunes SET name = ? WHERE id = ?", (new_name, tune_id))
        conn.close()

    def delete_tune(self, tune_id):
        """Hide a tune from the library. Its row is kept so sessions and switch history still resolve it."""
        if self.get_tune(tune_id)['origin'] == 'stock':
            raise TuneInUse(f"Tune {tune_id} is the stock tune and cannot be deleted")
        conn = self._connect()
        try:
            profiles = [r['name'] for r in conn.execute("SELECT name FROM profiles WHERE tune_id = ?", (tune_id,))]
            if profiles:
                raise TuneInUse(f"Tune {tune_id} is assigned to profile(s): {', '.join(profiles)}")
            if conn.execute("SELECT 1 FROM car_state WHERE active_tune_id = ?", (tune_id,)).fetchone():
                raise TuneInUse(f"Tune {tune_id} is the active tune")
            with conn:
                conn.execute("UPDATE tunes SET deleted_at = ? WHERE id = ?", (_now(), tune_id))
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
        """Add a tune from a .lmtune file to this car's library, unapproved, and return its new id."""
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
        return self.save_tune(name, data, payload.get('notes'), origin='imported')

if __name__ == "__main__":
    tm = TuneManager(1)
    tm.save_tune("Race Mode", b"tune_binary_data")
    print("Tunes:", [tuple(t) for t in tm.list_tunes()])
