# tune_switcher.py

import threading
from dataclasses import dataclass

from tune_management.car_database import connect_car_db, utc_now
from tune_management.ecu_backend import ECUError, SoftwareBackend
from tune_management.profiles import ProfileManager, UnknownProfile
from tune_management.tune_manager import TuneManager, TuneNotFound

SOURCES = ('voice', 'dashboard', 'app', 'manual', 'auto')

# One switch at a time per process; flashing may take minutes and must not interleave.
_switch_lock = threading.Lock()

@dataclass
class SwitchResult:
    ok: bool
    method: str
    active_tune_id: int = None
    active_profile: str = None
    previous_tune_id: int = None
    reason: str = None
    error: str = None  # None, 'not_found', 'refused' or 'failed'

class TuneSwitcher:
    """The single way to change a car's active tune (voice, dashboard, app, manual, auto)."""

    def __init__(self, car_id, backend=None, engine_rpm=None):
        self.car_id = car_id
        self.backend = backend or SoftwareBackend()
        self.engine_rpm = engine_rpm  # callable returning rpm or None; needed for flash backends
        self.tunes = TuneManager(car_id)
        self.profiles = ProfileManager(car_id)

    def active(self):
        """Return {'tune_id', 'tune_name', 'profile', 'updated_at'} for the car's active tune."""
        conn = connect_car_db(self.car_id)
        row = conn.execute('''
            SELECT s.active_tune_id AS tune_id, t.name AS tune_name, s.active_profile AS profile, s.updated_at
            FROM car_state s LEFT JOIN tunes t ON t.id = s.active_tune_id
        ''').fetchone()
        conn.close()
        return dict(row)

    def history(self, limit=50):
        """Switch attempts, newest first."""
        conn = connect_car_db(self.car_id)
        rows = conn.execute("SELECT * FROM tune_switches ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r, success=bool(r['success'])) for r in rows]

    def switch(self, source, profile=None, tune_id=None):
        """Activate a profile's tune or a specific tune. Every attempt is recorded in the history."""
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}, not {source!r}")
        if (profile is None) == (tune_id is None):
            raise ValueError("pass exactly one of profile or tune_id")

        with _switch_lock:
            previous = self.active()['tune_id']
            if source == 'auto' and tune_id is not None:
                # Automation may only pick between profiles a person has already set up.
                result = SwitchResult(False, self.backend.method, previous_tune_id=previous, error='refused',
                                      reason="Automatic switching may only select a profile, not a specific tune")
            else:
                result = self._attempt(profile, tune_id, previous)
            self._record(source, profile, tune_id, result)
            return result

    def revert_to_stock(self, source):
        """Activate the car's stock tune. Allowed from every source; the usual backend and engine rules apply."""
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}, not {source!r}")
        with _switch_lock:
            previous = self.active()['tune_id']
            stock = self.tunes.get_stock_tune()
            if stock is None:
                result = SwitchResult(False, self.backend.method, previous_tune_id=previous, error='refused',
                                      reason=f"Car {self.car_id} has no stock tune to revert to")
            else:
                result = self._attempt(None, stock['id'], previous)
            self._record(source, None, stock['id'] if stock else None, result, kind='revert')
            return result

    def _attempt(self, profile, tune_id, previous):
        def fail(error, reason):
            return SwitchResult(False, self.backend.method, previous_tune_id=previous, reason=reason, error=error)

        profile_name = None
        try:
            if profile is not None:
                assigned = self.profiles.get(profile)
                profile_name = assigned['name']
                if assigned['tune_id'] is None:
                    return fail('refused', f"No tune is assigned to the {profile_name} profile")
                tune_id = assigned['tune_id']
            tune = self.tunes.get_tune(tune_id)
        except (UnknownProfile, TuneNotFound) as e:
            return fail('not_found', str(e))
        if not tune['approved']:
            return fail('refused', f"Tune '{tune['name']}' ({tune['origin']}) is not approved")

        if self.backend.method == 'flash':
            rpm = self.engine_rpm() if self.engine_rpm else None
            if rpm is None or rpm != 0:
                shown = 'unknown' if rpm is None else f"{rpm:.0f} rpm"
                return fail('refused', f"Engine must be off to flash a tune (engine speed: {shown})")

        try:
            self.backend.apply(tune)
        except ECUError as e:
            return fail('failed', f"ECU backend error: {e}")

        conn = connect_car_db(self.car_id)
        with conn:
            conn.execute("UPDATE car_state SET active_tune_id = ?, active_profile = ?, updated_at = ?",
                         (tune['id'], profile_name, utc_now()))
        conn.close()
        return SwitchResult(True, self.backend.method, active_tune_id=tune['id'], active_profile=profile_name,
                            previous_tune_id=previous)

    def _record(self, source, profile, tune_id, result, kind='switch'):
        conn = connect_car_db(self.car_id)
        with conn:
            conn.execute('''
                INSERT INTO tune_switches (timestamp, source, kind, requested_profile, requested_tune_id,
                                           from_tune_id, to_tune_id, method, success, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (utc_now(), source, kind, profile, tune_id, result.previous_tune_id, result.active_tune_id,
                  result.method, int(result.ok), result.reason))
        conn.close()
if __name__ == "__main__":
    switcher = TuneSwitcher(1)
    print(switcher.switch('manual', profile='street'))
    print(switcher.active())
