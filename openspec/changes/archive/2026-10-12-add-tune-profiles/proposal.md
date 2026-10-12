# Proposal

## Why

Section 3 of `copilot_implementation_plan.md` (Tune Management) is next. Today a car's tunes can only be saved and listed; there is no notion of Race/Street profiles, no way to switch the active tune, no record of what was active when, and no way to share a tune. Voice commands, dashboard buttons and the mobile app (Sections 4–5) all need one switching service to call, so it has to exist first.

Lightman is meant to be plug-and-play through the OBD-II port, with no wiring into the ECU. This change therefore switches tunes in software only, behind an ECU backend interface designed so that a GPIO map-switch backend and full-image flashing (engine off only) can be added later without changing callers.

## What Changes

- Manage each car's tune library: save, list, get, rename, and delete tunes, and export/import a tune as a portable file for sharing.
- Add tune profiles: every car gets `race` and `street` profiles, and each can be assigned a tune from that car's library.
- Add a single switching service that activates a profile or tune for a car and persists which one is active. Every switch records its source (voice, dashboard, app, manual, auto).
- Introduce an ECU backend interface that declares how a switch is applied (`software`, `live` map switch, or `flash`). Ship only the `software` backend now. Any `flash` switch is refused unless the engine is confirmed off.
- Record every switch attempt (success or refusal) as tune history, and tag new logging sessions with the active tune by default.
- Add REST endpoints for profiles, tunes and switching, so a dashboard button or app can drive them. Stop `dashboard.py` from connecting to OBD at import time.

## Capabilities

### New Capabilities
- `tune-library`: Storing, retrieving, renaming, deleting, exporting and importing a car's tunes.
- `tune-profiles`: Race/Street profiles per car and their tune assignments.
- `tune-switching`: Activating a profile or tune through an ECU backend, safety gating, active-tune state, and switch history.

### Modified Capabilities
- None. `telemetry-logging` is still an unarchived change, so the default session tune is covered in `tune-switching`.

## Impact

- New: `tune_management/profiles.py`, `tune_management/tune_switcher.py`, `tune_management/ecu_backend.py`, `user_interface/api.py`, with tests.
- Modified: `tune_management/tune_manager.py` (get/rename/delete/export/import), `tune_management/car_database.py` (`profiles`, `car_state`, `tune_switches` tables), `data_acquisition/data_logger.py` (default `--tune-id` to the active tune), `user_interface/dashboard.py`.
- No new dependencies (Flask is already required).
- Out of scope: data-driven tune recommendations (separate change), voice command parsing (Section 4), GPIO map-switch and ECU flashing backends (later changes), street-legality checks (Section 6), cloud sharing (Section 7).
