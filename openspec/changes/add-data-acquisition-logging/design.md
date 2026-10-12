# Design

## Context

- `OBDReader` constructs `obd.OBD()` in its constructor (auto-scans serial ports, slow, needs hardware) and returns raw `pint` quantities. It calls `response.is_successful()`, which python-OBD's `OBDResponse` does not provide (it has `is_null()`).
- `tune_management/tune_manager.py` and `performance_report.py` do `from car_database import ...`, which only works when run from inside that folder; `from tune_management.tune_manager import TuneManager` (used by tests and `integration_main.py`) fails.
- `car_database.py` creates `car_databases/` at import time relative to the current directory.
- No Python dependencies are installed locally; `requirements.txt` contains entries pip cannot install.
- Target runtime is a Raspberry Pi 5; development and tests must run on a laptop with no OBD adapter or GPS.

## Goals / Non-Goals

**Goals:**
- All new behavior testable without hardware via injected connection/line sources.
- Single-threaded, synchronous logging loop that is easy to reason about on the Pi.
- Schema that later sections (reports, recommendations, dashboard) can query with plain SQL.

**Non-Goals:**
- Multi-PID batching / async python-OBD watchers (optimize later if 1–5 Hz is insufficient).
- Track database, sector timing, predictive lap delta.
- Migrating or changing the existing `tunes` / `logs` tables.

## Decisions

**Synchronous poll loop.** Each tick the logger (1) drains all buffered NMEA lines from the GPS, feeding every new fix to the lap timer, (2) queries the OBD PIDs, (3) writes one sample row, then sleeps until the next tick. Alternative: a background GPS thread with callbacks — rejected because it needs locking around the lap timer and SQLite connection for no real benefit at these rates.

**Lap timing uses GPS UTC time, not read time.** Because fixes are drained in batches once per tick, the time a line was read is not when the fix happened. RMC sentences carry UTC date+time, so the lap timer works in GPS epoch seconds and lap durations are exact differences of interpolated crossing times. Lap start/end are converted to session-elapsed seconds using an offset captured from the first fix of the session.

**Crossing detection in a local flat projection.** Fixes and line endpoints are projected to metres with an equirectangular projection around the line's midpoint (error is negligible over a few hundred metres) and tested with a standard segment-intersection test; the intersection parameter along the fix-to-fix segment gives the interpolated crossing time.

**Hand-written NMEA RMC parser.** RMC gives validity, lat/lon, speed and UTC date/time — everything needed. Parsing it (plus checksum) is ~40 lines; `pynmea2` was considered but adds a dependency for one sentence type. Accepts any talker id (`GP`, `GN`, `GL`…).

**Injectable sources.** `OBDReader(connection=None)` creates `obd.OBD()` lazily only if none is given. `GPSReader(line_source)` takes any object with a non-blocking `readline()`-like interface; a helper opens a `pyserial` port with a zero timeout for real hardware.

**Bounded adapter connect.** python-OBD's auto-detect opens every serial port and blocks indefinitely on unpaired Bluetooth serial ports (observed on Windows `COM3`/`COM4`; same risk with `/dev/rfcomm*` on the Pi). `connect()` runs `obd.OBD()` in a daemon thread with a timeout (default 30 s) and falls back to a null connection, and the CLI connects before opening the session so the session never starts behind a blocked call.

**Explicit columns for samples.** `samples` has one column per PID plus `latitude`, `longitude`, `gps_speed`, `lap_number`, `elapsed`, `wall_time`. A JSON blob was considered for flexibility, but explicit columns keep reporting queries simple; new sensors can add columns later via plugins.

**Database root resolved at call time.** `car_database.DB_ROOT` defaults to `$LIGHTMAN_DB_ROOT` or `car_databases`, is created in `init_car_db`, and is read when paths are built so tests can point it at a temp directory.

## Risks / Trade-offs

- [Serial OBD queries are slow (~50–100 ms each); six PIDs limit the practical rate to ~2 Hz] → Rate is configurable; the loop never sleeps a negative interval and simply runs as fast as it can when behind.
- [GPS at 1 Hz gives lap times accurate only to the interpolation quality] → Interpolation between fixes; recommend a 10 Hz receiver in the README.
- [Equirectangular projection breaks for very long lines or near the poles] → Start/finish lines are tens of metres; acceptable.
- [Session not closed if the process is killed] → `ended_at` stays null; reports can treat that as an aborted session.
