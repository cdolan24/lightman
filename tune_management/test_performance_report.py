# test_performance_report.py

import io
import json

import pytest

from tune_management.car_database import connect_car_db
from tune_management.performance_report import (SessionNotFound, fmt_lap, list_sessions, main, session_report,
                                                tune_comparison)
from tune_management.tune_manager import TuneManager

TRACK_A = [40.0, -105.0, 40.0001, -105.0]
TRACK_B = [41.0, -106.0, 41.0001, -106.0]

def add_session(started='2026-10-12T10:00:00+00:00', ended='2026-10-12T10:30:00+00:00', tune_id=None, line=None,
                laps=(), samples=()):
    """laps: (duration, tune_id); samples: dicts of sample columns."""
    conn = connect_car_db(1)
    with conn:
        sid = conn.execute("INSERT INTO sessions (started_at, ended_at, tune_id, lap_line) VALUES (?, ?, ?, ?)",
                           (started, ended, tune_id, json.dumps(line) if line else None)).lastrowid
        for n, (duration, lap_tune) in enumerate(laps, 1):
            conn.execute("INSERT INTO laps (session_id, lap_number, start_elapsed, end_elapsed, duration, tune_id) "
                         "VALUES (?, ?, 0, 0, ?, ?)", (sid, n, duration, lap_tune))
        for sample in samples:
            cols = ['session_id', 'wall_time', 'elapsed', *sample]
            conn.execute(f"INSERT INTO samples ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                         [sid, started, 0, *sample.values()])
    conn.close()
    return sid

@pytest.fixture
def tunes():
    tm = TuneManager(1)
    return tm.save_tune("Race", b"r"), tm.save_tune("Street", b"s")

def test_list_sessions(tunes):
    race, _ = tunes
    ids = [add_session(tune_id=race, laps=[(90, race)] * n) for n in (0, 2, 1)]
    sessions = list_sessions(1)
    assert [s['id'] for s in sessions] == ids[::-1]
    assert [s['lap_count'] for s in sessions] == [1, 2, 0]
    assert sessions[0]['duration'] == 1800 and sessions[0]['tune_name'] == "Race"

def test_three_laps(tunes):
    race, _ = tunes
    r = session_report(1, add_session(laps=[(95.0, race), (92.0, race), (93.0, race)]))
    assert r['best_lap']['lap_number'] == 2 and r['best_lap']['duration'] == 92.0
    assert r['average_lap'] == pytest.approx(93.333, abs=1e-3)
    assert r['lap_stdev'] == pytest.approx(1.528, abs=1e-3)
    assert [lap['tune_name'] for lap in r['laps']] == ["Race"] * 3

def test_no_laps():
    r = session_report(1, add_session())
    assert r['laps'] == [] and r['best_lap'] is None and r['average_lap'] is None and r['lap_stdev'] is None

def test_single_lap_has_no_stdev(tunes):
    r = session_report(1, add_session(laps=[(90.0, tunes[0])]))
    assert r['average_lap'] == 90.0 and r['lap_stdev'] is None

def test_engine_stats():
    samples = [{'rpm': 3000.0, 'coolant_temp': 85.0, 'fuel_level': 60.0},
               {'rpm': 6800.0, 'coolant_temp': 104.0, 'fuel_level': None},
               {'rpm': None, 'coolant_temp': 95.0, 'fuel_level': 52.0}]
    engine = session_report(1, add_session(samples=samples))['engine']
    assert engine['max_rpm'] == 6800 and engine['max_coolant'] == 104
    assert engine['avg_coolant'] == pytest.approx(94.667, abs=1e-3)
    assert engine['fuel_used'] == 8 and engine['max_intake'] is None and engine['samples'] == 3

def test_unknown_session():
    with pytest.raises(SessionNotFound):
        session_report(1, 999)

def test_tune_comparison(tunes):
    race, street = tunes
    add_session(line=TRACK_A, laps=[(90.0, race), (92.0, race), (96.0, street)])
    add_session(line=TRACK_B, laps=[(70.0, race)])
    add_session(line=TRACK_A, laps=[(80.0, None)])            # unknown tune: excluded
    add_session(laps=[(60.0, race)])                          # no line: excluded
    tracks = {tuple(t['line']): t['tunes'] for t in tune_comparison(1)}
    assert set(tracks) == {tuple(TRACK_A), tuple(TRACK_B)}
    a = [(t['tune_name'], t['best_lap'], t['average_lap'], t['laps']) for t in tracks[tuple(TRACK_A)]]
    assert a == [("Race", 90.0, 91.0, 2), ("Street", 96.0, 96.0, 1)]
    assert [(t['tune_name'], t['laps']) for t in tracks[tuple(TRACK_B)]] == [("Race", 1)]

def test_cli(tunes, capsys):
    race, street = tunes
    sid = add_session(tune_id=race, line=TRACK_A, laps=[(95.0, race), (92.0, race)],
                      samples=[{'rpm': 6000.0, 'fuel_level': 50.0}])
    add_session(line=TRACK_A, laps=[(96.0, street)])
    out = io.StringIO()
    assert main(['--car-id', '1', '--session', str(sid)], out=out) == 0
    text = out.getvalue()
    assert "Lap  2  1:32.0  Race  best" in text and "Max rpm 6000" in text
    out = io.StringIO()
    main(['--car-id', '1', '--compare'], out=out)
    assert "Race" in out.getvalue() and "best 1:32.0  avg 1:33.5  2 lap(s)" in out.getvalue()
    out = io.StringIO()
    main(['--car-id', '1'], out=out)
    assert out.getvalue().count("lap(s)") == 2
    assert main(['--car-id', '1', '--session', '999']) == 1

def test_fmt_lap():
    assert fmt_lap(92.04) == "1:32.0" and fmt_lap(5.0) == "0:05.0" and fmt_lap(None) == "-"
    assert fmt_lap(59.96) == "1:00.0"
