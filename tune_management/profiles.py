# profiles.py

from tune_management.car_database import connect_car_db
from tune_management.tune_manager import TuneManager

class UnknownProfile(LookupError):
    pass

class ProfileManager:
    """A car's driving profiles (race, street, ...) and the tune assigned to each."""

    def __init__(self, car_id):
        self.car_id = car_id
        self.tunes = TuneManager(car_id)

    def list_profiles(self):
        """List of {'name', 'tune_id', 'tune_name'}; tune fields are None when unassigned."""
        conn = connect_car_db(self.car_id)
        rows = conn.execute('''
            SELECT p.name, p.tune_id, t.name AS tune_name
            FROM profiles p LEFT JOIN tunes t ON t.id = p.tune_id
            ORDER BY p.name
        ''').fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get(self, name):
        """Return the profile as a dict; raise UnknownProfile if it doesn't exist. Names are case-insensitive."""
        name = name.strip().lower()
        for profile in self.list_profiles():
            if profile['name'] == name:
                return profile
        raise UnknownProfile(f"Unknown profile '{name}' for car {self.car_id}")

    def assign(self, name, tune_id):
        """Point a profile at a tune from this car's library (raises TuneNotFound otherwise)."""
        profile = self.get(name)
        self.tunes.get_tune(tune_id)
        conn = connect_car_db(self.car_id)
        with conn:
            conn.execute("UPDATE profiles SET tune_id = ? WHERE name = ?", (tune_id, profile['name']))
        conn.close()

if __name__ == "__main__":
    print(ProfileManager(1).list_profiles())
