# Proposal

## Why

Section 2 of `copilot_implementation_plan.md` (Data Acquisition & Logging) is the next unimplemented part of the plan, and every later section (tune recommendations, real-time feedback, performance reports) depends on having recorded session data. Today `OBDReader` can only take a one-off snapshot, nothing is persisted, there is no GPS or lap timing, and the `tune_management` modules cannot be imported as a package, so the existing tests cannot run.

## What Changes

- Add continuous telemetry logging: sample OBD-II PIDs at a fixed rate during a session and persist each sample to the car's database, tagged with the active tune.
- Add a GPS reader that parses NMEA sentences from a serial GPS receiver into position fixes, and merge the latest fix into each telemetry sample.
- Add lap timing: detect start/finish line crossings from consecutive GPS fixes, record lap numbers and lap times, and tag samples with their lap.
- Make the OBD reader tolerate a disconnected adapter and accept an injected connection so it can be tested without hardware; serialize unit-bearing values to plain numbers for storage.
- Fix package imports in `tune_management` (`car_database` imported as a top-level module) and stop creating the database directory as an import side effect.
- Clean up `requirements.txt` (duplicates, non-installable entries such as `sqlite3`, `pyOBD`) and add `pyserial` and `pytest`.

## Capabilities

### New Capabilities
- `telemetry-logging`: Recording sessions of timestamped vehicle data (OBD-II PIDs plus GPS position) to the per-car database.
- `lap-timing`: Detecting start/finish line crossings from GPS and recording lap numbers and lap times for a session.

### Modified Capabilities
None (no existing specs).

## Impact

- New modules: `data_acquisition/gps_reader.py`, `data_acquisition/lap_timer.py`, `data_acquisition/data_logger.py`, with tests.
- Modified: `data_acquisition/obd_reader.py`, `tune_management/car_database.py` (new `sessions`, `samples`, `laps` tables; existing `tunes`/`logs` untouched), `tune_management/tune_manager.py`, `tune_management/performance_report.py`.
- Dependencies: adds `pyserial`, `pytest`; removes invalid entries from `requirements.txt`.
- Out of scope: lap-time analysis/reporting, dashboard display of live data, external sensors beyond GPS.
