# test_car_database.py

import sqlite3
import unittest

from tune_management.car_database import connect_car_db, get_db_path, init_car_db

class TestCarDatabase(unittest.TestCase):
    def test_migrates_old_schema_and_is_idempotent(self):
        get_db_path(1).parent.mkdir(parents=True, exist_ok=True)
        old = sqlite3.connect(get_db_path(1))
        old.execute("CREATE TABLE tunes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                    "data BLOB NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        old.execute("INSERT INTO tunes (name, data) VALUES ('Legacy', x'00')")
        old.commit()
        old.close()

        init_car_db(1)
        init_car_db(1)

        conn = connect_car_db(1)
        columns = {row['name'] for row in conn.execute("PRAGMA table_info(tunes)")}
        self.assertTrue({'notes', 'deleted_at'} <= columns)
        self.assertEqual(conn.execute("SELECT name FROM tunes").fetchone()['name'], 'Legacy')
        self.assertEqual(sorted(r['name'] for r in conn.execute("SELECT name FROM profiles")), ['race', 'street'])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM car_state").fetchone()[0], 1)
        legacy = conn.execute("SELECT origin, approved_by, approved_at FROM tunes").fetchone()
        self.assertEqual((legacy['origin'], legacy['approved_by']), ('human', 'migration'))
        self.assertIsNotNone(legacy['approved_at'])
        conn.close()

    def test_data_and_origin_are_immutable(self):
        conn = connect_car_db(1)
        with conn:
            conn.execute("INSERT INTO tunes (name, data, origin) VALUES ('Gen', x'01', 'generated')")
        for sql in ("UPDATE tunes SET data = x'02'", "UPDATE tunes SET origin = 'human'"):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                with conn:
                    conn.execute(sql)
        row = conn.execute("SELECT data, origin FROM tunes").fetchone()
        self.assertEqual((row['data'], row['origin']), (b'\x01', 'generated'))
        with conn:
            conn.execute("UPDATE tunes SET name = 'Renamed'")  # other columns stay editable
        conn.close()

    def test_only_one_stock_tune(self):
        conn = connect_car_db(1)
        with conn:
            conn.execute("INSERT INTO tunes (name, data, origin) VALUES ('Stock', x'00', 'stock')")
        with self.assertRaises(sqlite3.IntegrityError):
            with conn:
                conn.execute("INSERT INTO tunes (name, data, origin) VALUES ('Stock 2', x'00', 'stock')")
        conn.close()

if __name__ == "__main__":
    unittest.main()
