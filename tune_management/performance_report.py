# performance_report.py

"""Post-session reports and per-track tune comparisons from recorded sessions, samples and laps."""

import argparse
import json
import statistics
import sys
from datetime import datetime

from tune_management.car_database import connect_car_db

class SessionNotFound(LookupError):
    pass

def _duration(started_at, ended_at):
    if not ended_at:
        return None
    return (datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)).total_seconds()

def list_sessions(car_id):
    """Sessions newest first: id, started_at, ended_at, duration, tune_id, tune_name, lap_count."""
    conn = connect_car_db(car_id)
    rows = conn.execute('''
        SELECT s.id, s.started_at, s.ended_at, s.tune_id, t.name AS tune_name,
               (SELECT COUNT(*) FROM laps WHERE session_id = s.id) AS lap_count
        FROM sessions s LEFT JOIN tunes t ON t.id = s.tune_id
        ORDER BY s.id DESC
    ''').fetchall()
    conn.close()
    return [dict(r, duration=_duration(r['started_at'], r['ended_at'])) for r in rows]

def session_report(car_id, session_id):
    """Lap summary and engine stats for one session. Raises SessionNotFound."""
    conn = connect_car_db(car_id)
    try:
        session = conn.execute('''
            SELECT s.id, s.started_at, s.ended_at, s.tune_id, t.name AS tune_name, s.lap_line
            FROM sessions s LEFT JOIN tunes t ON t.id = s.tune_id WHERE s.id = ?
        ''', (session_id,)).fetchone()
        if session is None:
            raise SessionNotFound(f"Session {session_id} not found for car {car_id}")
        laps = [dict(r) for r in conn.execute('''
            SELECT l.lap_number, l.duration, l.tune_id, t.name AS tune_name
            FROM laps l LEFT JOIN tunes t ON t.id = l.tune_id
            WHERE l.session_id = ? ORDER BY l.lap_number
        ''', (session_id,))]
        stats = dict(conn.execute('''
            SELECT MAX(rpm) AS max_rpm, MAX(speed) AS max_speed, MAX(coolant_temp) AS max_coolant,
                   AVG(coolant_temp) AS avg_coolant, MAX(intake_temp) AS max_intake, COUNT(*) AS samples
            FROM samples WHERE session_id = ?
        ''', (session_id,)).fetchone())
        fuel = conn.execute('''
            SELECT (SELECT fuel_level FROM samples WHERE session_id = :s AND fuel_level IS NOT NULL ORDER BY id LIMIT 1),
                   (SELECT fuel_level FROM samples WHERE session_id = :s AND fuel_level IS NOT NULL ORDER BY id DESC LIMIT 1)
        ''', {'s': session_id}).fetchone()
    finally:
        conn.close()

    stats['fuel_used'] = fuel[0] - fuel[1] if fuel[0] is not None else None
    times = [lap['duration'] for lap in laps]
    best = min(laps, key=lambda lap: lap['duration']) if laps else None
    return {
        'session': dict(session, lap_line=json.loads(session['lap_line']) if session['lap_line'] else None,
                        duration=_duration(session['started_at'], session['ended_at'])),
        'laps': laps,
        'best_lap': best,
        'average_lap': statistics.fmean(times) if times else None,
        'lap_stdev': statistics.stdev(times) if len(times) >= 2 else None,
        'engine': stats,
    }

def tune_comparison(car_id):
    """Per track (start/finish line), each tune's best lap, average lap and lap count.

    Only laps with a recorded tune on a session with a recorded line are compared.
    """
    conn = connect_car_db(car_id)
    rows = conn.execute('''
        SELECT s.lap_line, l.tune_id, t.name AS tune_name,
               MIN(l.duration) AS best_lap, AVG(l.duration) AS average_lap, COUNT(*) AS laps
        FROM laps l JOIN sessions s ON s.id = l.session_id LEFT JOIN tunes t ON t.id = l.tune_id
        WHERE l.tune_id IS NOT NULL AND s.lap_line IS NOT NULL
        GROUP BY s.lap_line, l.tune_id
        ORDER BY s.lap_line, best_lap
    ''').fetchall()
    conn.close()
    tracks = {}
    for r in rows:
        tracks.setdefault(r['lap_line'], []).append(
            {k: r[k] for k in ('tune_id', 'tune_name', 'best_lap', 'average_lap', 'laps')})
    return [{'line': json.loads(line), 'tunes': tunes} for line, tunes in tracks.items()]

def fmt_lap(seconds):
    if seconds is None:
        return '-'
    minutes, rest = divmod(round(seconds, 1), 60)   # round first, or 59.96 becomes "0:60.0"
    return f"{int(minutes)}:{rest:04.1f}"

def _fmt(value, digits=0, unit=''):
    return '-' if value is None else f"{value:.{digits}f}{unit}"

def main(argv=None, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Session reports and tune comparisons.")
    parser.add_argument('--car-id', type=int, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--session', type=int, help="report for one session")
    group.add_argument('--compare', action='store_true', help="compare tunes per track")
    args = parser.parse_args(argv)
    p = lambda *a: print(*a, file=out)

    if args.session is not None:
        try:
            r = session_report(args.car_id, args.session)
        except SessionNotFound as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        s, e = r['session'], r['engine']
        p(f"Session {s['id']}  {s['started_at']}  duration {_fmt(s['duration'], 0, ' s')}  "
          f"tune {s['tune_name'] or '-'}")
        for lap in r['laps']:
            best = '  best' if r['best_lap'] and lap['lap_number'] == r['best_lap']['lap_number'] else ''
            p(f"  Lap {lap['lap_number']:>2}  {fmt_lap(lap['duration'])}  {lap['tune_name'] or 'unknown tune'}{best}")
        p(f"Average {fmt_lap(r['average_lap'])}  consistency (stdev) {_fmt(r['lap_stdev'], 2, ' s')}")
        p(f"Max rpm {_fmt(e['max_rpm'])}  max speed {_fmt(e['max_speed'], 0, ' km/h')}  "
          f"coolant max {_fmt(e['max_coolant'], 0, ' C')} avg {_fmt(e['avg_coolant'], 0, ' C')}  "
          f"intake max {_fmt(e['max_intake'], 0, ' C')}  fuel used {_fmt(e['fuel_used'], 1, ' %')}")
    elif args.compare:
        tracks = tune_comparison(args.car_id)
        if not tracks:
            p("No timed laps with a recorded tune yet.")
        for track in tracks:
            p(f"Track line {track['line']}")
            for t in track['tunes']:
                p(f"  {t['tune_name']:<20} best {fmt_lap(t['best_lap'])}  avg {fmt_lap(t['average_lap'])}  "
                  f"{t['laps']} lap(s)")
    else:
        for s in list_sessions(args.car_id):
            p(f"{s['id']:>4}  {s['started_at']}  {_fmt(s['duration'], 0, ' s'):>8}  "
              f"{s['lap_count']:>3} lap(s)  {s['tune_name'] or '-'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
