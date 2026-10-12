# Tasks

## 1. Setup and baseline fixes

- [x] 1.1 Clean up `requirements.txt` (dedupe; drop `pyOBD`, `python-OBD`, `sqlite3`; add `pyserial`, `pytest`), add `.venv/` and `car_databases/` to `.gitignore`, and verify `pip install -r requirements.txt` succeeds in a fresh venv
- [x] 1.2 Add `__init__.py` to each package and switch `tune_manager.py` / `performance_report.py` to package imports; verify `py -c "from tune_management.tune_manager import TuneManager"` works from the repo root
- [x] 1.3 Make `car_database` resolve `DB_ROOT` at call time (env `LIGHTMAN_DB_ROOT`), create it in `init_car_db`, and add `sessions`, `samples`, `laps` tables; add a `conftest.py` fixture pointing the DB root at a temp dir and verify `test_tune_manager.py` passes

## 2. OBD reader

- [x] 2.1 Make `OBDReader` accept an injected connection, create `obd.OBD()` lazily, use `is_null()`, catch query errors, return plain magnitudes, and bound the adapter connect with a timeout; verify with tests using a fake connection (values, missing PID, raising query, hanging connect)

## 3. GPS reader

- [x] 3.1 Implement `data_acquisition/gps_reader.py` (RMC parsing with checksum, any talker id, `poll()` returning new fixes, `latest_fix`, serial helper); verify with tests for valid fix, void fix, bad checksum, non-RMC sentence, and S/W hemispheres

## 4. Lap timer

- [x] 4.1 Implement `data_acquisition/lap_timer.py` (line definition, projected segment intersection with interpolated time, lap recording, min-lap debounce, current lap number); verify with tests for the spec scenarios (crossing at ~0.5 s, miss beside the line, two laps 90 s / 85 s, jitter ignored, out-lap null)

## 5. Data logger

- [x] 5.1 Implement `data_acquisition/data_logger.py` (start/stop session, `tick()` that drains GPS → lap timer → OBD → sample row, persists completed laps, `run()` loop with configurable rate/duration, CLI entry point); verify with tests for session start/stop with and without tune, sample fields, null GPS, disconnected adapter, laps persisted and samples lap-tagged
- [x] 5.2 Document running the logger (CLI flags, GPS recommendation) in `README.md` and verify `py -m data_acquisition.data_logger --help` prints the documented options

## 6. Integration check

- [x] 6.1 Run the full hardware-free test suite (`pytest data_acquisition tune_management`) and `openspec validate add-data-acquisition-logging --strict`; both pass
