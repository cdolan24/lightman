# car_database.py

import os
import sqlite3
from pathlib import Path

# Read at call time so tests (or a deployment) can point it elsewhere.
DB_ROOT = Path(os.environ.get('LIGHTMAN_DB_ROOT', 'car_databases'))

DEFAULT_PROFILES = ('race', 'street')

def get_db_path(car_id):
    """Return the path for a car's database file."""
    return Path(DB_ROOT) / f"car_{car_id}.db"

def init_car_db(car_id):
    """Initialize a database for a specific car."""
    Path(DB_ROOT).mkdir(parents=True, exist_ok=True)
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tune_id INTEGER,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            FOREIGN KEY(tune_id) REFERENCES tunes(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            wall_time TEXT NOT NULL,
            elapsed REAL NOT NULL,
            lap_number INTEGER,
            rpm REAL,
            speed REAL,
            throttle_pos REAL,
            coolant_temp REAL,
            intake_temp REAL,
            fuel_level REAL,
            latitude REAL,
            longitude REAL,
            gps_speed REAL,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            lap_number INTEGER NOT NULL,
            start_elapsed REAL NOT NULL,
            end_elapsed REAL NOT NULL,
            duration REAL NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    ''')
    # Columns added after the original tunes schema; migrate older databases in place.
    tune_columns = {row[1] for row in c.execute("PRAGMA table_info(tunes)")}
    for column in ('notes', 'deleted_at'):
        if column not in tune_columns:
            c.execute(f"ALTER TABLE tunes ADD COLUMN {column} TEXT")
    c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            tune_id INTEGER,
            FOREIGN KEY(tune_id) REFERENCES tunes(id)
        )
    ''')
    c.executemany("INSERT OR IGNORE INTO profiles (name) VALUES (?)", [(p,) for p in DEFAULT_PROFILES])
    c.execute('''
        CREATE TABLE IF NOT EXISTS car_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active_tune_id INTEGER,
            active_profile TEXT,
            updated_at TEXT,
            FOREIGN KEY(active_tune_id) REFERENCES tunes(id)
        )
    ''')
    c.execute("INSERT OR IGNORE INTO car_state (id) VALUES (1)")
    c.execute('''
        CREATE TABLE IF NOT EXISTS tune_switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            requested_profile TEXT,
            requested_tune_id INTEGER,
            from_tune_id INTEGER,
            to_tune_id INTEGER,
            method TEXT,
            success INTEGER NOT NULL,
            reason TEXT
        )
    ''')
    conn.commit()
    conn.close()

def connect_car_db(car_id):
    """Initialize (if needed) and open a car's database with rows accessible by column name."""
    init_car_db(car_id)
    conn = sqlite3.connect(get_db_path(car_id), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    # Example: Initialize DB for car with ID 1
    init_car_db(1)
    print(f"Database for car 1 initialized at {get_db_path(1)}")
