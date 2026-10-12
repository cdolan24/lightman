# Lightman

Lightman is an artificial agent for track/street cars, running on a Raspberry Pi 5. It connects to the car via OBD-II, provides real-time feedback, manages ECU tunes, and acts as a copilot for optimal performance.

## Features
- Data acquisition from OBD-II and sensors
- Continuous session logging with GPS position and lap timing
- Mode-based tune switching (race/street)
- Adaptive tuning recommendations
- Real-time voice assistant feedback
- Manual override controls
- Database for saving tunes and car profiles

## Project Structure
- `data_acquisition/` - OBD-II, GPS, lap timing, and session logging
- `tune_management/` - Tune switching, saving, and analysis
- `user_interface/` - Dashboard and app integration
- `voice_assistant/` - Text-to-speech and command handling
- `openspec/` - Specs and change proposals (OpenSpec)

## Getting Started
1. Create a virtualenv and install dependencies:
   ```
   python -m venv .venv
   .venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
   ```
2. Run the tests that need no hardware: `pytest data_acquisition tune_management`

## Logging a Session

```
python -m data_acquisition.data_logger --car-id 1 [options]
```

| Option | Description |
| --- | --- |
| `--car-id` | Car whose database (`car_databases/car_<id>.db`) receives the session (required) |
| `--tune-id` | Active tune to tag the session with |
| `--rate` | Samples per second (default 1). Six PIDs over a serial ELM327 limits this to roughly 2 Hz |
| `--duration` | Stop after this many seconds (default: run until Ctrl+C) |
| `--obd-port` | OBD-II adapter port (default: auto-detect) |
| `--obd-timeout` | Seconds to wait for the adapter before logging without engine data (default 30). Auto-detect can hang on unpaired Bluetooth serial ports, so set `--obd-port` when you know it |
| `--gps-port`, `--gps-baud` | Serial port and baud rate (default 9600) of an NMEA GPS receiver |
| `--line LAT1,LON1,LAT2,LON2` | Start/finish line endpoints; enables lap timing (requires `--gps-port`) |
| `--min-lap-time` | Ignore line crossings closer together than this many seconds (default 10) |

Each session writes to the `sessions`, `samples` (RPM, speed, throttle, coolant/intake temp, fuel level, latitude/longitude, GPS speed, lap number) and `laps` tables. Lap times are interpolated between GPS fixes, so a 10 Hz receiver gives noticeably better accuracy than a 1 Hz one. Place the start/finish line endpoints on either side of the track so the line spans its full width.

Set `LIGHTMAN_DB_ROOT` to store car databases somewhere other than `./car_databases`.

## Tunes, Profiles and Switching

Each car's library holds its tunes. In `TuneManager` you can save, get, rename and delete them. Deleted tunes are hidden but kept, so old sessions still resolve the tune they ran. To share a tune, export it to a portable `.lmtune` file and import it into another car.

### Tune safety: provenance, approval and stock

Every tune records its **origin**:
- `human` and `stock` tunes are approved when they're saved.
- `imported` and `generated` tunes start **unapproved**. They can't be assigned to a profile or activated until a person approves them by name from the dashboard, the app or the CLI. `voice` and `auto` can never approve a tune.
- Tune data and origin can't be changed after saving (a database trigger enforces this), so an approval always covers exactly the bytes that were reviewed. To change a tune, save a new one.

Each car can hold one protected **stock tune**, which can't be deleted. **Revert to stock** works from every source, including `auto` and `voice`, and still obeys the engine-off rule for flashing. The `auto` source may only switch by profile, never to an arbitrary tune.

Tunes that existed before provenance tracking were approved automatically with `approved_by = migration`. Review them with `tune_cli list`.

```
python -m tune_management.tune_cli --car-id 1 list
python -m tune_management.tune_cli --car-id 1 save-stock stock.bin [--name Stock]
python -m tune_management.tune_cli --car-id 1 import shared.lmtune
python -m tune_management.tune_cli --car-id 1 approve 4 --by Connor [--note "checked timing/AFR"]
```

### Profiles and switching

Every car has a `race` and a `street` profile, and each can point at a tune from that car's library (`ProfileManager`). Only approved tunes can be assigned. All switching goes through `TuneSwitcher.switch(source, profile=... | tune_id=...)`, where `source` is one of `voice`, `dashboard`, `app`, `manual` or `auto`. The active tune persists across restarts. Every attempt is recorded in the `tune_switches` history, including refused ones, and new logging sessions are tagged with the active tune by default.

**ECU backends.** A switch is applied through an ECU backend (`tune_management/ecu_backend.py`), and the backend's method is reported with every result:

| Method | Status | Behaviour |
| --- | --- | --- |
| `software` | Default | Records the selection only and does not communicate with the ECU. This keeps Lightman plug-and-play via OBD-II |
| `live` | Planned | Flips the ECU's map-switch input (e.g. from a GPIO pin) for instant switching while driving |
| `flash` | Planned | Writes the full tune image. Only allowed when the engine is confirmed off (0 rpm); refused if the engine is running or rpm can't be read |

> ⚠️ **Tune safety is an open issue.** Approval, the `auto` restriction and the protected stock tune are in place, but tune contents are not validated and there is no safety envelope yet. See [docs/open-issues/tune-safety.md](docs/open-issues/tune-safety.md). The remaining items must be resolved before any `live`/`flash` backend or tune generation ships.

### HTTP API

`python -m user_interface.dashboard` serves these endpoints on port 5000:

| Method & path | Body | Description |
| --- | --- | --- |
| `GET /api/obd` | | Live OBD-II readings |
| `GET /api/cars/<id>/tunes` | | The car's tune library, with `origin`, `approved`, `approved_by` and `approved_at` |
| `POST /api/cars/<id>/tunes/<tune_id>/approve` | `{"source": "dashboard", "approved_by": "Connor", "note": "..."}` | Approve a tune. `403` if the source isn't `dashboard`/`app`/`manual` or the name is missing |
| `GET /api/cars/<id>/profiles` | | Profiles and their assigned tunes |
| `PUT /api/cars/<id>/profiles/<name>` | `{"tune_id": 3}` | Assign a tune to a profile (`409` if it isn't approved) |
| `GET /api/cars/<id>/active` | | Active tune and profile |
| `POST /api/cars/<id>/switch` | `{"source": "dashboard", "profile": "race"}` or `{"source": "app", "tune_id": 3}` | Switch tunes. `200` on success, `404` if the profile or tune is unknown, `409` if refused or the ECU failed (with `reason`) |
| `POST /api/cars/<id>/revert` | `{"source": "voice"}` | Revert to the stock tune (`409` if there's no stock tune or it was refused) |
| `GET /api/cars/<id>/history?limit=50` | | Switch history, newest first (`kind` is `switch` or `revert`) |

> The API has no authentication yet, so anyone on the Pi's network can switch tunes. That is acceptable while switching is software-only, but authentication **must** be added before a `live` or `flash` backend ships.

## Notes
- Each car has a dedicated database for tunes and logs.
- Designed for extensibility and future features.

Only thing I can't do with this is find my 10mm
