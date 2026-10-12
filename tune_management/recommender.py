# recommender.py

"""Advisory profile suggestions from live telemetry.

Recommendations are for the driver to act on. Nothing here switches, creates or changes a tune
(tune safety, GitHub #1).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from tune_management.car_database import connect_car_db

DEFAULT_LIMITS = {
    'coolant_hot': 105.0,       # °C at or above: running hot
    'intake_heat_soak': 60.0,   # °C at or above: intake air heat-soaked
    'coolant_warm': 70.0,       # °C below: engine not warmed up
    'max_sample_age': 10.0,     # seconds; older samples aren't "live"
}

@dataclass
class Recommendation:
    rule: str
    severity: str               # 'info' or 'warning'
    suggested_profile: str      # or None
    reason: str
    values: dict = field(default_factory=dict)

class Recommender:
    def __init__(self, car_id, limits=None, clock=None):
        self.car_id = car_id
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _live_sample(self, conn):
        sample = conn.execute('''
            SELECT * FROM samples WHERE session_id = (SELECT MAX(id) FROM sessions)
            ORDER BY id DESC LIMIT 1
        ''').fetchone()
        if sample is None:
            return None
        age = (self.clock() - datetime.fromisoformat(sample['wall_time'])).total_seconds()
        return sample if age <= self.limits['max_sample_age'] else None

    def recommend(self):
        """Return a list of Recommendation for the car's current state (empty without live data)."""
        conn = connect_car_db(self.car_id)
        try:
            profile = conn.execute("SELECT active_profile FROM car_state").fetchone()['active_profile']
            sample = self._live_sample(conn)
        finally:
            conn.close()
        if sample is None:
            return []

        coolant, intake, lap = sample['coolant_temp'], sample['intake_temp'], sample['lap_number']
        limits = self.limits
        recs = []
        if profile == 'race':
            if coolant is not None and coolant >= limits['coolant_hot']:
                recs.append(Recommendation(
                    'race_overheating', 'warning', 'street',
                    f"Coolant is {coolant:.0f} °C (limit {limits['coolant_hot']:.0f} °C) on the race profile; "
                    "switch to street to reduce engine load.", {'coolant_temp': coolant}))
            if intake is not None and intake >= limits['intake_heat_soak']:
                recs.append(Recommendation(
                    'race_heat_soak', 'warning', 'street',
                    f"Intake air is {intake:.0f} °C (limit {limits['intake_heat_soak']:.0f} °C), so the engine is "
                    "heat-soaked; switch to street until it cools.", {'intake_temp': intake}))
            if coolant is not None and coolant < limits['coolant_warm']:
                recs.append(Recommendation(
                    'race_cold_engine', 'info', 'street',
                    f"Coolant is only {coolant:.0f} °C; use street until the engine reaches "
                    f"{limits['coolant_warm']:.0f} °C.", {'coolant_temp': coolant}))
        elif profile == 'street' and lap is not None:
            healthy = (coolant is not None and intake is not None
                       and limits['coolant_warm'] <= coolant < limits['coolant_hot']
                       and intake < limits['intake_heat_soak'])
            if healthy:
                recs.append(Recommendation(
                    'track_on_street', 'info', 'race',
                    f"On a timed lap (lap {lap}) with a healthy engine; the race profile is available.",
                    {'lap_number': lap, 'coolant_temp': coolant, 'intake_temp': intake}))
        return recs

if __name__ == "__main__":
    for rec in Recommender(1).recommend():
        print(rec)
