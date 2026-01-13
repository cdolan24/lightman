# car_database.py

import sqlite3
from pathlib import Path

DB_ROOT = Path('car_databases')
DB_ROOT.mkdir(exist_ok=True)

def get_db_path(car_id):
    """Return the path for a car's database file."""
    return DB_ROOT / f"car_{car_id}.db"

def init_car_db(car_id):
    """Initialize a database for a specific car."""
    db_path = get_db_path(car_id)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tunes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tune_id INTEGER,
            log_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tune_id) REFERENCES tunes(id)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Example: Initialize DB for car with ID 1
    init_car_db(1)
    print(f"Database for car 1 initialized at {get_db_path(1)}")
