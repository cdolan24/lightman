# Proposal

## Why

Lightman is meant to be drag-and-drop software for a Pi: copy it on, plug the Pi into the car, and it works. Today it is several separate commands (data logger, feedback monitor, dashboard), each with its own flags, and nothing starts at boot. Running the dashboard next to the logger also has a hazard. Its engine-speed check for the flash safety gate queries the OBD-II adapter directly, which competes with the logger for the same serial adapter.

## What Changes

- Add a single entry point, `python -m lightman`. It runs the data logger, the spoken feedback monitor and the dashboard/API server together in one process, configured from one TOML file.
- **Configuration:** `lightman.toml` (path from `--config` or `LIGHTMAN_CONFIG`). Every setting has a default, so the service runs with no file at all. Unknown keys or invalid values stop startup with a message naming the setting.
- **Resilient startup:**
  - A missing OBD-II adapter, GPS receiver or audio output degrades that one feature (logged clearly) instead of stopping the service.
  - A crash in one component is logged and doesn't take down the others.
- **The logger is the only OBD-II reader:** the tune switcher's engine-speed check uses the latest recorded sample (at most 2 s old), never the adapter. When no fresh sample exists, engine speed is treated as unknown, so a flash stays refused.
- **Clean shutdown:** on SIGTERM or Ctrl+C the session is closed with its end time, queued speech is abandoned and the server stops.
- **Pi deployment:** a systemd unit and an install script that creates the virtualenv and enables start-at-boot, plus an example config.
- Each power-up of the Pi (i.e. each drive) is one logging session.

## Capabilities

### New Capabilities
- `lightman-service`: The combined Lightman process, its configuration, resilience, shutdown and Pi deployment.

### Modified Capabilities
None. The data logger gains a stop signal, but its specified behaviour does not change.

## Impact

- New: the `lightman/` package (`__main__.py`, `config.py`, `service.py`), `deploy/lightman.service`, `deploy/install.sh`, `lightman.example.toml`, with tests.
- Modified: `DataLogger.run` accepts a stop event. `user_interface/dashboard.py` exposes an app factory so the service can provide its own switcher (with engine speed from samples).
- No new dependencies (`tomllib` is in the Python 3.11+ standard library, which is the Raspberry Pi OS Bookworm default).
- Out of scope: voice commands (needs a speech-recognition decision), authentication, and starting or stopping sessions on engine on/off.
