# Proposal

## Why

Section 7 of the plan calls for post-session performance reports covering lap times, engine stats and tune effectiveness. Lightman now records sessions, samples, laps and tune switches, but nothing summarizes them. The existing `PerformanceReport` reads the legacy `logs` table, which nothing writes to anymore. To judge tune effectiveness, each lap must also be tied to the tune that was active when it was driven and to the track it was timed on, because lap times from different tracks can't be compared.

## What Changes

- Each recorded lap stores the tune that was active when the lap completed.
- Each session with lap timing stores its start/finish line, which identifies the track.
- **Session report:**
  - Duration and the tune at session start.
  - Laps: count, each lap with its tune, best, average, and consistency (standard deviation).
  - Engine stats: max rpm, max speed, max and average coolant, max intake air, and fuel used.
- **Tune comparison:** for each tune, best lap, average lap and lap count. Computed per track (start/finish line), so only laps on the same line are compared.
- Interfaces:
  - CLI: `python -m tune_management.performance_report --car-id N [--session S | --compare]`.
  - HTTP: `GET /sessions`, `GET /sessions/<sid>/report`, `GET /tune-comparison`.
- Replace the legacy `logs`-based `PerformanceReport`.

## Capabilities

### New Capabilities
- `performance-reports`: Session reports and per-track tune comparisons.

### Modified Capabilities
- `lap-timing`: laps record the active tune, and sessions record their start/finish line.

## Impact

- Modified: `tune_management/car_database.py` (`laps.tune_id`, `sessions.lap_line` with migration), `data_acquisition/data_logger.py` (records both), `tune_management/performance_report.py` (rewritten), `user_interface/api.py`.
- Laps recorded before this change have no tune. Reports show them as "unknown tune" and leave them out of tune comparisons.
- No new dependencies.
- Out of scope: charts (companion app), spoken session summaries, cloud sharing.
