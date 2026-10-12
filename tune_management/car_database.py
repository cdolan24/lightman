# car_database.py

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Read at call time so tests (or a deployment) can point it elsewhere.
DB_ROOT = Path(os.environ.get('LIGHTMAN_DB_ROOT', 'car_databases'))

DEFAULT_PROFILES = ('race', 'street')

# Database files whose schema has been created/migrated by this process.
_initialized = set()

def utc_now():
    """Current UTC time as an ISO 8601 string, the timestamp format used in every table."""
    return datetime.now(timezone.utc).isoformat()

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
    added = _add_columns(c, 'tunes', {
        'notes': 'TEXT',
        'deleted_at': 'TEXT',
        'origin': "TEXT NOT NULL DEFAULT 'human'",
        'approved_at': 'TEXT',
        'approved_by': 'TEXT',
        'approval_note': 'TEXT',
    })
    if 'origin' in added:
        # Tunes that predate provenance were saved by a person; approve them, marked for review.
        c.execute("UPDATE tunes SET approved_at = ?, approved_by = 'migration' WHERE approved_at IS NULL",
                  (utc_now(),))
    # Approval covers exact bytes and origin, so neither may change after saving, whoever writes the SQL.
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS tunes_immutable
        BEFORE UPDATE OF data, origin ON tunes
        BEGIN
            SELECT RAISE(ABORT, 'tune data and origin are immutable; save a new tune instead');
        END
    ''')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_stock_tune ON tunes(origin) WHERE origin = 'stock'")
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
    _add_columns(c, 'tune_switches', {'kind': "TEXT NOT NULL DEFAULT 'switch'"})
    _add_columns(c, 'laps', {'tune_id': 'INTEGER'})          # tune active when the lap completed
    _add_columns(c, 'sessions', {'lap_line': 'TEXT'})        # JSON [lat1, lon1, lat2, lon2]; identifies the track
    conn.commit()
    conn.close()
    _initialized.add(Path(db_path).resolve())

def _add_columns(c, table, columns):
    """Add any missing columns to table; return the names that were added."""
    existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
    added = [name for name in columns if name not in existing]
    for name in added:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {columns[name]}")
    return added

def connect_car_db(car_id):
    """Initialize (once per process) and open a car's database with rows accessible by column name."""
    db_path = get_db_path(car_id)
    if db_path.resolve() not in _initialized or not db_path.exists():
        init_car_db(car_id)
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    # Example: Initialize DB for car with ID 1
    init_car_db(1)
    print(f"Database for car 1 initialized at {get_db_path(1)}")
