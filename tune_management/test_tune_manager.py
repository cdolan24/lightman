# test_tune_manager.py

import json
import unittest

import pytest

from tune_management.car_database import connect_car_db
from tune_management.tune_manager import InvalidTuneFile, TuneInUse, TuneManager, TuneNotFound

class TestTuneManager(unittest.TestCase):
    def test_save_and_list_tune(self):
        tm = TuneManager(99)  # Use a test car ID
        tm.save_tune("Test Tune", b"test_data")
        tunes = tm.list_tunes()
        self.assertTrue(any(t[1] == "Test Tune" for t in tunes))

    def test_get_tune(self):
        tm = TuneManager(1)
        tune_id = tm.save_tune("Track Day", b"\x01\x02", notes="E85")
        tune = tm.get_tune(tune_id)
        self.assertEqual((tune['name'], tune['data'], tune['notes']), ("Track Day", b"\x01\x02", "E85"))

    def test_unknown_tune(self):
        with self.assertRaises(TuneNotFound):
            TuneManager(1).get_tune(42)

    def test_tunes_are_scoped_to_car(self):
        TuneManager(1).save_tune("Car one only", b"x")
        self.assertEqual(list(TuneManager(2).list_tunes()), [])

    def test_rename(self):
        tm = TuneManager(1)
        tune_id = tm.save_tune("Old", b"data")
        tm.rename_tune(tune_id, "New")
        self.assertEqual([t['name'] for t in tm.list_tunes()], ["New"])
        self.assertEqual(tm.get_tune(tune_id)['data'], b"data")

    def test_delete_hides_tune(self):
        tm = TuneManager(1)
        tune_id = tm.save_tune("Gone", b"x")
        tm.delete_tune(tune_id)
        self.assertEqual(list(tm.list_tunes()), [])
        with self.assertRaises(TuneNotFound):
            tm.get_tune(tune_id)

    def test_delete_assigned_or_active_is_refused(self):
        tm = TuneManager(1)
        assigned = tm.save_tune("Race", b"r")
        active = tm.save_tune("Street", b"s")
        conn = connect_car_db(1)
        with conn:
            conn.execute("UPDATE profiles SET tune_id = ? WHERE name = 'race'", (assigned,))
            conn.execute("UPDATE car_state SET active_tune_id = ?", (active,))
        conn.close()
        for tune_id in (assigned, active):
            with self.assertRaises(TuneInUse):
                tm.delete_tune(tune_id)
        self.assertEqual(len(tm.list_tunes()), 2)

def test_export_import_between_cars(tmp_path):
    src = TuneManager(1)
    tune_id = src.save_tune("Shared", bytes(range(256)), notes="93 octane")
    path = tmp_path / "shared.lmtune"
    src.export_tune(tune_id, path)

    dst = TuneManager(2)
    new_id = dst.import_tune(path)
    tune = dst.get_tune(new_id)
    assert (tune['name'], tune['notes'], tune['data']) == ("Shared", "93 octane", bytes(range(256)))

@pytest.mark.parametrize("content", [
    "not json",
    json.dumps({"format": "something-else", "version": 1, "name": "x", "data": ""}),
    json.dumps({"format": "lightman-tune", "version": 1, "name": "x", "data": "***"}),
    json.dumps({"format": "lightman-tune", "version": 1}),
    json.dumps([1, 2]),
])
def test_import_invalid_file(tmp_path, content):
    path = tmp_path / "bad.lmtune"
    path.write_text(content)
    tm = TuneManager(1)
    with pytest.raises(InvalidTuneFile):
        tm.import_tune(path)
    assert list(tm.list_tunes()) == []

if __name__ == "__main__":
    unittest.main()
