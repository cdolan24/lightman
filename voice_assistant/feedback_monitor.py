# feedback_monitor.py

"""Turns what's happening in a car's database into spoken copilot feedback."""

import threading
import time

from tune_management.car_database import connect_car_db
from tune_management.recommender import Recommender

DEFAULT_LIMITS = {
    'coolant_critical': 110.0,   # °C at or above: warn
    'coolant_rearm_drop': 5.0,   # °C below critical before the alert re-arms
    'fuel_low': 10.0,            # % at or below: announce
    'obd_loss_samples': 5,       # consecutive samples without rpm before announcing data loss
    'repeat_interval': 60.0,     # seconds before repeating a still-active coolant alert
}

def say_lap_time(seconds):
    """92.4 -> '1 minute 32.4 seconds'."""
    minutes, rest = divmod(round(seconds, 1), 60)
    secs = f"{rest:.1f} seconds"
    if not minutes:
        return secs
    return f"{int(minutes)} minute{'s' if minutes != 1 else ''} {secs}"

class FeedbackMonitor:
    def __init__(self, car_id, announcer, limits=None, recommender=None, clock=time.monotonic):
        self.car_id = car_id
        self.announcer = announcer
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.recommender = recommender or Recommender(car_id)
        self.clock = clock
        # Only announce what happens after we start.
        conn = connect_car_db(car_id)
        self._last_lap_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM laps").fetchone()[0]
        self._last_switch_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tune_switches").fetchone()[0]
        conn.close()
        self._session_id = None
        self._active_recommendations = set()

    def _reset_session_state(self, session_id):
        self._session_id = session_id
        self._coolant_alerted_at = None
        self._fuel_alerted = False
        self._had_engine_data = False
        self._engine_data_lost = False

    def check(self):
        """Poll once and queue any announcements."""
        conn = connect_car_db(self.car_id)
        try:
            session = conn.execute("SELECT id, ended_at FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
            if session is not None and session['ended_at'] is None:
                if session['id'] != self._session_id:
                    self._reset_session_state(session['id'])
                self._check_engine(conn, session['id'])
            self._check_laps(conn)
            self._check_switches(conn)
        finally:
            conn.close()
        self._check_recommendations()

    def _check_engine(self, conn, session_id):
        n = self.limits['obd_loss_samples']
        recent = conn.execute("SELECT rpm, coolant_temp, fuel_level FROM samples WHERE session_id = ? "
                              "ORDER BY id DESC LIMIT ?", (session_id, n)).fetchall()
        if not recent:
            return
        latest = recent[0]
        say = self.announcer.say

        coolant, critical = latest['coolant_temp'], self.limits['coolant_critical']
        if coolant is not None:
            if coolant >= critical:
                alerted = self._coolant_alerted_at
                if alerted is None or self.clock() - alerted >= self.limits['repeat_interval']:
                    say(f"Warning: coolant temperature {coolant:.0f} degrees. Ease off and let the engine cool.",
                        'warning')
                    self._coolant_alerted_at = self.clock()
            elif coolant <= critical - self.limits['coolant_rearm_drop']:
                self._coolant_alerted_at = None

        fuel = latest['fuel_level']
        if fuel is not None:
            if fuel <= self.limits['fuel_low'] and not self._fuel_alerted:
                say(f"Fuel is low, {fuel:.0f} percent remaining.")
                self._fuel_alerted = True
            elif fuel > self.limits['fuel_low']:
                self._fuel_alerted = False

        if latest['rpm'] is not None:
            self._had_engine_data = True
            if self._engine_data_lost:
                say("Engine data is back.")
                self._engine_data_lost = False
        elif (self._had_engine_data and not self._engine_data_lost and len(recent) == n
              and all(r['rpm'] is None for r in recent)):
            say("Warning: lost engine data from the OBD adapter.", 'warning')
            self._engine_data_lost = True

    def _check_laps(self, conn):
        for lap in conn.execute("SELECT * FROM laps WHERE id > ? ORDER BY id", (self._last_lap_id,)).fetchall():
            best = conn.execute("SELECT MIN(duration) FROM laps WHERE session_id = ? AND id <= ?",
                                (lap['session_id'], lap['id'])).fetchone()[0]
            text = f"Lap {lap['lap_number']}, {say_lap_time(lap['duration'])}"
            if lap['lap_number'] > 1 and lap['duration'] <= best:
                text += ", best lap"
            self.announcer.say(text + ".")
            self._last_lap_id = lap['id']

    def _check_switches(self, conn):
        rows = conn.execute('''
            SELECT s.*, t.name AS tune_name FROM tune_switches s LEFT JOIN tunes t ON t.id = s.to_tune_id
            WHERE s.id > ? ORDER BY s.id
        ''', (self._last_switch_id,)).fetchall()
        for row in rows:
            self._last_switch_id = row['id']
            if row['source'] == 'voice':
                continue  # the voice command handler answers its own commands
            if not row['success']:
                self.announcer.say(f"Tune switch refused: {row['reason']}", 'warning')
                continue
            if row['kind'] == 'revert':
                text = "Reverted to the stock tune."
            elif row['requested_profile']:
                text = f"{row['requested_profile'].strip().title()} profile selected."
            else:
                text = f"Tune {row['tune_name']} selected."
            if row['method'] == 'software':
                text += " Software only; the ECU was not changed."
            self.announcer.say(text)

    def _check_recommendations(self):
        current = {}
        for rec in self.recommender.recommend():
            current[rec.rule] = rec
        for rule in current.keys() - self._active_recommendations:
            rec = current[rule]
            self.announcer.say(rec.reason, 'warning' if rec.severity == 'warning' else 'info')
        self._active_recommendations = set(current)

    def run(self, interval=1.0, stop_event=None):
        """Poll until stop_event is set."""
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            self.check()
            stop_event.wait(interval)

def main(argv=None):
    import argparse
    from voice_assistant.announcer import Announcer
    from voice_assistant.voice_feedback import VoiceAssistant

    parser = argparse.ArgumentParser(description="Speak copilot feedback for a car.")
    parser.add_argument('--car-id', type=int, required=True)
    parser.add_argument('--interval', type=float, default=1.0, help="seconds between checks (default 1)")
    args = parser.parse_args(argv)

    announcer = Announcer(VoiceAssistant().speak)
    announcer.say("Lightman copilot online.")
    try:
        FeedbackMonitor(args.car_id, announcer).run(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        announcer.stop()

if __name__ == "__main__":
    main()
