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

## Notes
- Each car has a dedicated database for tunes and logs.
- Designed for extensibility and future features.

Only thing I can't do with this is find my 10mm
