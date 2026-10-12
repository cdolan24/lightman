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
- `docs/` - [Product philosophy](docs/product-philosophy.md), [companion app](docs/companion-app.md), [extensibility](docs/extensibility.md), [open issues](docs/open-issues/)
- `copilot_implementation_plan.md` - Roadmap with per-section status

## Quick Start on a Raspberry Pi

1. Copy this repository onto the Pi (Raspberry Pi OS Bookworm or newer, Python 3.11+), plug in the OBD-II adapter (and GPS receiver, if you have one), then run:
   ```
   bash deploy/install.sh
   sudo systemctl start lightman
   ```
   The install script creates the virtualenv, installs `requirements.txt`, copies `lightman.example.toml` to `/etc/lightman.toml` (if there isn't one already), adds you to the `dialout` and `audio` groups, and enables the `lightman` systemd service. From then on, Lightman starts every time the Pi boots and restarts if it crashes.
2. Open the dashboard at `http://<pi-hostname>.local:5000/`. Logs are at `journalctl -u lightman -f`.

`python -m lightman [--config PATH]` runs everything in one process: the data logger (the only process that talks to the OBD-II adapter), spoken feedback, and the dashboard/API. Each boot is one logging session, and sessions left open by a power cut are closed on the next start. If the OBD-II adapter, GPS or audio is missing, only that feature is disabled (with a log message). A component that crashes is restarted without stopping the others.

### Configuration

Settings come from a TOML file: `--config`, else `$LIGHTMAN_CONFIG`, else `./lightman.toml`. The installed service uses `/etc/lightman.toml`. Every setting is optional, and a typo or invalid value stops startup with an error naming the setting. See `lightman.example.toml`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `car_id` | `1` | Which car's database to use |
| `db_root` | `"car_databases"` | Where car databases live (relative to the install directory) |
| `obd.port` | `""` | OBD-II adapter port (e.g. `/dev/ttyUSB0`, `/dev/rfcomm0`). `""` means auto-detect |
| `obd.timeout` | `30.0` | Seconds to wait for the adapter before logging without engine data |
| `logging.rate` | `1.0` | Samples per second (about 2 is the practical max over an ELM327) |
| `gps.port` | `""` | NMEA GPS receiver port (e.g. `/dev/ttyACM0`). `""` means no GPS |
| `gps.baud` | `9600` | GPS baud rate |
| `lap_timing.line` | `[]` | Start/finish line `[lat1, lon1, lat2, lon2]`. Needs `gps.port` |
| `lap_timing.min_lap_time` | `10.0` | Ignore line crossings closer together than this (s) |
| `dashboard.host` | `"0.0.0.0"` | Use `"127.0.0.1"` to allow only a screen attached to the Pi |
| `dashboard.port` | `5000` | Dashboard/API port |
| `voice.enabled` | `true` | Spoken copilot feedback |
| `override.pin` | `-1` | BCM GPIO pin of the physical override button/switch. `-1` means none |
| `override.mode` | `"button"` | `"button"` or `"switch"` (see below) |
| `override.long_press` | `2.0` | Seconds to hold the button for revert to stock |

> Not yet verified on real Pi hardware: audio output from a system service. If voice is silent under systemd, check `journalctl -u lightman` for "voice feedback disabled". The rest of the service is unaffected.

### Physical override

Wire a momentary button (or a toggle switch) between a free GPIO pin and GND. The Pi's internal pull-up is used, so no resistor is needed. Set `override.pin` to the pin's BCM number, e.g. `17` for physical pin 11. Nothing connects to the ECU.

- **Button mode:** a short press toggles the profile. From street it goes to race; from anything else (race, stock, a directly chosen tune) it goes to street, so the default direction is the safer one. Holding for `long_press` seconds **reverts to stock**.
- **Switch mode:** on selects race and off selects street. The current position is applied when Lightman starts.

Override actions are normal `manual` switches. Approval and engine-off rules apply, they appear in the switch history, and the copilot announces them.

## Development

Install `requirements-dev.txt` and run `pytest`. Tests that need real hardware are skipped unless you run `pytest -m hardware`. The components below can also be run on their own for development or debugging.

## Logging a Session

```
python -m data_acquisition.data_logger --car-id 1 [options]
```

| Option | Description |
| --- | --- |
| `--car-id` | Car whose database (`car_databases/car_<id>.db`) receives the session (required) |
| `--tune-id` | Tune to tag the session with (default: the car's active tune) |
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

### Recommendations (advisory)

`Recommender` (`tune_management/recommender.py`) compares the latest live sample with the active profile and suggests a profile. It never switches tunes. The driver decides, and `auto` switching on recommendations is deliberately not implemented (tune safety #1). It returns nothing if the newest sample is older than `max_sample_age`.

| Rule | When | Suggests |
| --- | --- | --- |
| `race_overheating` (warning) | On `race` with coolant ≥ `coolant_hot` (105 °C) | `street` |
| `race_heat_soak` (warning) | On `race` with intake air ≥ `intake_heat_soak` (60 °C) | `street` |
| `race_cold_engine` (info) | On `race` with coolant < `coolant_warm` (70 °C) | `street` |
| `track_on_street` (info) | On `street` during a timed lap, with coolant and intake inside those limits | `race` |

The limits (`DEFAULT_LIMITS`, plus `max_sample_age` = 10 s) can be overridden per `Recommender`.

### HTTP API

`python -m user_interface.dashboard` serves the **live dashboard** at `http://<pi>:5000/` (`/?car=<id>`, default car 1). It shows:
- Live readings, which turn amber or red near the alert limits and are marked stale when no sample has arrived for over 5 s.
- Laps (current, last and best).
- The active tune, with honest status about the switch method.
- Recommendations and recent switches.
- Race, Street and **Revert to stock** buttons.

It is fully self-contained and needs no internet in the car. Tune approval is deliberately not offered there; use the CLI or the companion app.

The same server provides these endpoints:

| Method & path | Body | Description |
| --- | --- | --- |
| `GET /api/obd` | | Queries the OBD-II adapter directly. Don't use it while the data logger runs; use `/live` |
| `GET /api/cars/<id>/live` | | The in-progress session from recorded data: latest `sample` (with `age_seconds`), `laps` and `best_lap` |
| `GET /api/cars/<id>/tunes` | | The car's tune library, with `origin`, `approved`, `approved_by` and `approved_at` |
| `POST /api/cars/<id>/tunes/<tune_id>/approve` | `{"source": "dashboard", "approved_by": "Connor", "note": "..."}` | Approve a tune. `403` if the source isn't `dashboard`/`app`/`manual` or the name is missing |
| `GET /api/cars/<id>/profiles` | | Profiles and their assigned tunes |
| `PUT /api/cars/<id>/profiles/<name>` | `{"tune_id": 3}` | Assign a tune to a profile (`409` if it isn't approved) |
| `GET /api/cars/<id>/active` | | Active tune and profile |
| `POST /api/cars/<id>/switch` | `{"source": "dashboard", "profile": "race"}` or `{"source": "app", "tune_id": 3}` | Switch tunes. `200` on success, `404` if the profile or tune is unknown, `409` if refused or the ECU failed (with `reason`) |
| `POST /api/cars/<id>/revert` | `{"source": "voice"}` | Revert to the stock tune (`409` if there's no stock tune or it was refused) |
| `GET /api/cars/<id>/sessions` | | Sessions, newest first, with duration, starting tune and lap count |
| `GET /api/cars/<id>/sessions/<sid>/report` | | Session report: laps (with tune), best, average, consistency and engine stats. `404` if the session is unknown |
| `GET /api/cars/<id>/tune-comparison` | | Best and average lap per tune, grouped by track (start/finish line) |
| `GET /api/cars/<id>/recommendations` | | Current advisory recommendations (`rule`, `severity`, `suggested_profile`, `reason`, `values`) |
| `GET /api/cars/<id>/history?limit=50` | | Switch history, newest first (`kind` is `switch` or `revert`) |

> The API has no authentication yet, so anyone on the Pi's network can switch tunes. That is acceptable while switching is software-only, but authentication **must** be added before a `live` or `flash` backend ships.

## Performance Reports

```
python -m tune_management.performance_report --car-id 1               # list sessions
python -m tune_management.performance_report --car-id 1 --session 12  # one session's report
python -m tune_management.performance_report --car-id 1 --compare     # tune comparison per track
```

- **Session report:** every lap with the tune it was driven on, plus best, average and consistency (standard deviation). Engine stats: max rpm and speed, max and average coolant, max intake air, and fuel used.
- **Tune comparison:** only compares laps on the **same start/finish line**, so lap times from different tracks are never mixed. Each lap is credited to the tune active when it finished. Laps recorded before tune attribution existed are left out.

## Spoken Copilot Feedback

```
python -m voice_assistant.feedback_monitor --car-id 1 [--interval 1]
```

The feedback monitor polls the car's database once a second and speaks through a non-blocking queue (`voice_assistant/announcer.py`). Warnings are spoken first, duplicates are collapsed, and messages that waited too long (15 s, or 30 s for warnings) are dropped instead of spoken late. It works alongside the data logger and the dashboard, whichever process wrote the data.

| Announcement | When (defaults in `feedback_monitor.DEFAULT_LIMITS`) |
| --- | --- |
| Coolant warning | Coolant ≥ `coolant_critical` (110 °C) during a session. Repeats after `repeat_interval` (60 s) if it stays hot, and re-arms once coolant falls `coolant_rearm_drop` (5 °C) below the limit |
| Low fuel | Fuel ≤ `fuel_low` (10 %). Once, then again only after refuelling |
| Engine data lost / back | No rpm in the last `obd_loss_samples` (5) samples after the session had engine data |
| Lap time | Each completed lap, e.g. "Lap 2, 1 minute 32.4 seconds, best lap" |
| Recommendations | When a recommendation first appears (warnings as warnings) |
| Tune switches | Results of switches not made by voice. Software-only switches say the ECU was not changed, and refusals give the reason |

## Notes
- Each car has a dedicated database for tunes and logs.
- Tune authoring, voice training data and local model updates will live in a separate [companion app](docs/companion-app.md), keeping this repository drag-and-drop for the Pi.

Only thing I can't do with this is find my 10mm
