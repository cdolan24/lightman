# Design

## Context

- Each car has its own SQLite file (`car_databases/car_<id>.db`) with `tunes`, `logs`, `sessions`, `samples` and `laps` tables. `TuneManager` can only save and list tunes.
- `ManualOverride` keeps its state in memory only and is not connected to anything. Section 5 (Manual Override) will build on the switching service from this change.
- `user_interface/dashboard.py` constructs `OBDReader()` at import time and exposes a single `/api/obd` route.
- Lightman is meant to be plug-and-play through the OBD-II port. Real ECU control comes later through two backends: a GPIO map-switch output (`live`) and full-image flashing with the engine off (`flash`).

## Goals / Non-Goals

**Goals:**
- One `TuneSwitcher` entry point that every caller (voice, dashboard, app, manual, future auto-tuner) uses.
- An ECU backend seam that lets a GPIO or flashing backend be added later without changing callers or the database.
- Safety rules enforced in the switcher, not left to each backend.

**Non-Goals:**
- Any real ECU communication, GPIO, or flashing protocol.
- Authentication for the HTTP API (it runs on the Pi's local network; security comes with the mobile app work in Section 5).
- Recommendations or automatic switching logic.

## Decisions

**Profiles as rows, seeded on init.** A `profiles(name PRIMARY KEY, tune_id)` table is seeded with `race` and `street` (`INSERT OR IGNORE`) in `init_car_db`. Names are lowercased on the way in. This is a table rather than two hard-coded columns, so adding more profiles later (e.g. `rain`, `valet`) is a data change, not a schema change.

**Active state in a single-row `car_state` table.** It holds `active_tune_id`, `active_profile` and `updated_at`, constrained by `CHECK (id = 1)`. The active tune is persisted per car, so it survives restarts and other processes (dashboard, logger) can read it.

**Switch flow serialised by a process lock, short DB writes.** The flow is: resolve the target, check the engine-off gate, call `backend.apply()`, update `car_state`, then insert a `tune_switches` row. It runs under one module-level lock, so concurrent requests (voice and dashboard at the same moment) apply one at a time. The `car_state` update and the history insert are each short transactions. Holding a SQLite write lock across `backend.apply()` (originally planned with `BEGIN IMMEDIATE`) was rejected: a future flash can take minutes and would block the data logger's sample writes past the busy timeout. Voice, dashboard and the API are expected to run in one Lightman process, so a process lock is enough. Refusals and backend errors still write a history row (unsuccessful) and leave `car_state` untouched.

**ECU backend interface.** `ECUBackend` has a `method` attribute (`software` | `live` | `flash`) and `apply(tune) -> None`, which raises `ECUError` on failure. `SoftwareBackend.apply` does nothing. A `BACKENDS` registry maps names to classes for later configuration. The engine-off gate lives in the switcher and keys off `backend.method == 'flash'`, so no future flashing backend can bypass it.

**Engine state through an injected callable.** `TuneSwitcher(car_id, backend=None, engine_rpm=None)`, where `engine_rpm` returns a float or `None`. It is wired to `OBDReader` in the app, and tests pass a lambda. Unknown rpm counts as "not off", because refusing a flash is safe and flashing a running engine is not.

**Soft delete for tunes.** Sessions and switch history reference tune ids, so deleting a tune sets `deleted_at` instead of removing the row. Deleted tunes disappear from listings and lookups but stay resolvable for history. The alternative was a hard delete with `ON DELETE SET NULL`, which was rejected because it would erase which tune a past session ran on. Existing `tunes` tables gain `notes` and `deleted_at` columns through `ALTER TABLE ... ADD COLUMN` when they are missing.

**Export format.** The export is a JSON file (`.lmtune`) of the form `{"format": "lightman-tune", "version": 1, "name", "notes", "data": <base64>}`. JSON was chosen over a raw `.bin` so the file carries a name and notes and can be validated on import. Tune images are kilobytes to a few MB, so base64 overhead does not matter.

**HTTP API as a Flask blueprint.** `user_interface/api.py` defines the routes under `/api/cars/<car_id>/...`. `dashboard.py` registers the blueprint and creates its `OBDReader` lazily, which removes the import-time hardware connection. Refusals return `409` with `{"ok": false, "reason"}`. Unknown cars, tunes or profiles return `404`.

## Risks / Trade-offs

- [Software-only switching means the ECU does not actually change yet] → Every switch result reports `method: software`, so the UI and voice feedback can say so plainly instead of implying the car changed.
- [The unauthenticated API could let anyone on the Pi's Wi-Fi switch tunes] → This is acceptable while switching is software-only. It must be revisited before a `live` or `flash` backend ships, and that is noted as a prerequisite in the README.
- [Two separate processes switching at once could interleave their backend calls] → Run all switch entry points in the single Lightman process. Add a cross-process lock file if that ever changes, before a `flash` backend ships.
