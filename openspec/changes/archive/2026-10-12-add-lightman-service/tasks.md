# Tasks

## 1. Building blocks

- [x] 1.1 Give `DataLogger.run` a `stop_event`, and add `close_stale_sessions(car_id)` (end time = last sample's time, or the start time if there are no samples). Verify with tests that `run` exits promptly when the event is set and that stale sessions are closed
- [x] 1.2 Add `sampled_engine_rpm(car_id, max_age)` and a `create_app(switcher_factory)` factory in `user_interface/dashboard.py`, keeping the module-level `app` for standalone use. Verify with tests for fresh, stale and absent samples, and that the factory app serves `/` and the API

## 2. Configuration

- [x] 2.1 Implement `lightman/config.py` (`DEFAULTS`, `load_config(path)` with unknown-key, type and range errors naming the dotted key, missing file means defaults) and `lightman.example.toml`. Verify with tests for no file, a full file, a typo key, a bad value, and that the example file loads cleanly

## 3. Service

- [x] 3.1 Implement `lightman/service.py` (`LightmanService(config, obd_connect, open_gps, make_speak)` with `start()`, `stop()` and `wait()`, supervised threads, degraded startup for OBD, GPS and voice, stale-session cleanup, and the server on the configured host and port) and `lightman/__main__.py` (`--config`, `LIGHTMAN_CONFIG`, signal handling, logging setup). Verify with tests that start the service with fakes on an ephemeral port: samples are recorded, `/api/cars/<id>/live` responds, voice and GPS failures degrade, a crashing component is restarted while the others keep running, and `stop()` records the session end time
- [x] 3.2 Smoke-test `python -m lightman` with a temp config and no adapter (short OBD timeout). Verify that it serves the dashboard, records samples, and exits cleanly with the session closed on Ctrl+C (CTRL_BREAK on Windows)

## 4. Deployment and docs

- [x] 4.1 Add `deploy/lightman.service` and `deploy/install.sh`. Verify that `bash -n deploy/install.sh` passes and review the unit manually (`systemd-analyze` was not available on the dev machine; first real check happens on a Pi)
- [x] 4.2 Update `README.md` (Quick start on a Pi, configuration reference generated from `DEFAULTS`, running individual components still possible) and `copilot_implementation_plan.md`. Verify that every key in `DEFAULTS` appears in the README and in `lightman.example.toml`

## 5. Integration check

- [x] 5.1 Run `pytest` and `openspec validate add-lightman-service --strict`, and confirm both pass
