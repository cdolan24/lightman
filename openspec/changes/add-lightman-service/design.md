# Design

## Context

- `DataLogger.run()` loops until a duration elapses or a `KeyboardInterrupt`. `FeedbackMonitor.run()` already takes a stop event. The dashboard is a module-level Flask `app` whose `SWITCHER_FACTORY` reads rpm via `OBDReader`, which directly queries the adapter.
- The target is Raspberry Pi OS Bookworm (Python 3.11, systemd). The Pi is typically powered from the car, so it boots when the car starts and loses power when it stops.

## Goals / Non-Goals

**Goals:**
- One process with one config file and start-at-boot, so nothing has to be done by hand on the Pi after install.
- Exactly one component talks to the OBD-II adapter.
- Hardware faults degrade features rather than stop the copilot.

**Non-Goals:**
- Multi-car per Pi (one `car_id` per config).
- Engine-on/off session detection (power cycle = session for now).
- Hot-reloading the config.

## Decisions

**One process, three threads.** Logger thread, monitor thread, and a werkzeug `make_server` HTTP server thread, all coordinated by one `threading.Event`. Separate processes were considered, but they would need IPC, and SQLite already acts as the shared bus. One process also makes the in-process switch lock (from `add-tune-profiles`) cover every switch entry point, which that design depended on.

**Component supervision.** Each thread body is wrapped so an unexpected exception is logged and that component is restarted after a short back-off (5 s), unless shutdown is in progress. systemd `Restart=on-failure` covers the whole process.

**Config as TOML validated against a schema of defaults.** `config.py` holds a nested `DEFAULTS` dict. Loading walks the file, rejects keys absent from `DEFAULTS` (catches typos like `prot`), and type-checks and range-checks values. The result is a plain dict. TOML is in the stdlib, readable and supports comments. JSON was rejected (no comments) and YAML would add a dependency.

**Engine speed from samples.** `sampled_engine_rpm(car_id, max_age=2.0)` reads the latest sample of the open session and returns `rpm`, or `None` if it is missing or stale. The service passes it to `TuneSwitcher` through the dashboard app factory (`create_app(switcher_factory)`). The standalone `python -m user_interface.dashboard` keeps its current behaviour.

**Session boundaries.** The logger starts a session at service start and closes it on shutdown. After a power cut the session has no `ended_at`. On the next start the service closes any still-open sessions, setting `ended_at` to their last sample's time, so the dashboard and feedback monitor only ever see the new session as live.

**Shutdown.** `SIGTERM` and `SIGINT` handlers set the stop event. Threads exit, the logger closes the session, the server is shut down, and the announcer is stopped. Pending speech is dropped, because it's stale by then.

**Deployment.** `deploy/lightman.service` runs `.venv/bin/python -m lightman --config /etc/lightman.toml`, with `WorkingDirectory` set to the install dir, `Restart=on-failure`, and the user in the `dialout` (serial) and `audio` groups. `deploy/install.sh` (run from the repo directory) creates the venv, installs requirements, copies the example config to `/etc/lightman.toml` if absent, renders the unit with the install path and user, and enables it.

## Risks / Trade-offs

- [Power loss can leave the last samples unwritten] → Samples are committed per tick, so at most one sample is lost. Stale open sessions are closed on the next boot.
- [A crash-looping component logs noisily] → The 5 s back-off between restarts, and journald rate limiting.
- [Dashboard on 0.0.0.0 without auth] → Unchanged risk, tracked in #1. Binding host is configurable (e.g. `127.0.0.1` for a screen attached to the Pi).
