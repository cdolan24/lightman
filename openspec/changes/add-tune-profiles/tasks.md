# Tasks

## 1. Schema

- [x] 1.1 Extend `init_car_db`: add `notes` and `deleted_at` to `tunes` (migrating existing DBs), and add `profiles` (seeded `race`/`street`), `car_state` (single row) and `tune_switches` tables. Verify with a test that initialising an old-schema DB twice migrates it and leaves exactly two profiles

## 2. Tune library

- [x] 2.1 Add `get_tune`, `rename_tune`, `delete_tune` (soft delete, refused when assigned or active) and `notes` support to `TuneManager`, with listings excluding deleted tunes. Verify with tests for fetch, unknown id, rename, per-car isolation, delete, and refused delete
- [x] 2.2 Add `export_tune(tune_id, path)` / `import_tune(path)` using the `.lmtune` JSON format. Verify with tests for a round trip between two cars and refusal of an invalid file

## 3. Profiles

- [x] 3.1 Implement `tune_management/profiles.py` (list profiles, assign a tune, resolve a name case-insensitively, unknown-profile error, refuse tunes from other cars or deleted tunes). Verify with tests covering the `tune-profiles` spec scenarios

## 4. Switching

- [x] 4.1 Implement `tune_management/ecu_backend.py` (`ECUBackend`, `ECUError`, `SoftwareBackend`, `BACKENDS` registry). Verify that `SoftwareBackend().method == 'software'` in a test
- [x] 4.2 Implement `tune_management/tune_switcher.py` (switch by profile or tune id, source validation, engine-off gate for `flash`, backend errors, persisted active state, history on success and refusal, `active()` and `history()`). Verify with tests for every `tune-switching` scenario except HTTP and sessions, using fake backends and rpm callables

## 5. Integration points

- [x] 5.1 Make `DataLogger.start()` default `tune_id` to the car's active tune. Verify with a test that a session started after a switch is tagged with the active tune
- [x] 5.2 Add the `user_interface/api.py` blueprint (tunes, profiles, assign, active, switch, history), register it in `dashboard.py`, and make `OBDReader` lazy there. Verify with Flask test-client tests for a successful switch, a 409 refusal and a 404 unknown profile, and verify that importing `dashboard` does not touch OBD
- [x] 5.3 Document profiles, switching, the backend roadmap (`live` GPIO, `flash` engine-off) and the API endpoints in `README.md`, including the note that the API must gain authentication before a `live`/`flash` backend ships. Verify that the documented endpoints match the blueprint's routes

## 6. Integration check

- [x] 6.1 Run `pytest data_acquisition tune_management user_interface` and `openspec validate add-tune-profiles --strict`, and confirm both pass
