# tune_manager.py

import sqlite3
from pathlib import Path
from car_database import get_db_path, init_car_db

class TuneManager:
    def __init__(self, car_id):
        self.car_id = car_id
        self.db_path = get_db_path(car_id)
        init_car_db(car_id)

    def save_tune(self, name, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO tunes (name, data) VALUES (?, ?)", (name, data))
        conn.commit()
        conn.close()

    def list_tunes(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, created_at FROM tunes")
        tunes = c.fetchall()
        conn.close()
        return tunes

if __name__ == "__main__":
    tm = TuneManager(1)
    tm.save_tune("Race Mode", b"tune_binary_data")
    print("Tunes:", tm.list_tunes())
