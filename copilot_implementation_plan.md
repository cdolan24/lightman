# Lightman Copilot Implementation Plan

Status key: **done** · **partial** · **todo** · **blocked** (with reason). Implemented behaviour is specified in `openspec/specs/`.

## Tools for Implementation

### Hardware
- Raspberry Pi 5 (central hub), OBD-II adapter (USB or Bluetooth ELM327)
- GPS receiver (NMEA, 10 Hz recommended for lap timing)
- CAN bus adapter (if needed)
- External sensors (optional: tire temp, brake pressure, etc.)

### Software & Libraries
- ECU tuning: TunerPro RT (primary), MegaSquirt TunerStudio, ECUFlash (Mitsubishi/Subaru), HP Tuners VCM Suite (GM/Ford). These are used from the [companion app](docs/companion-app.md), not on the Pi
- OBD-II diagnostic tools (ScanTool, Torque, etc.)
- Plotly or Matplotlib (data visualization)
- OpenCV (camera/sensor integration, optional)
- Scikit-learn or TensorFlow (machine learning for predictive maintenance/tuning)
- Requests/HTTPx (API calls), Bluetooth/WiFi libraries (wireless communication)
- AWS/GCP/Azure or Firebase (cloud storage / mobile backend, optional)

### Development & Testing
- CI/CD tools (GitHub Actions)
- Hardware simulators/emulators (for bench testing)

---

## 1. Core System Architecture — partial
- **done** Raspberry Pi 5 as central hub, connected to the car's OBD-II port for ECU data
- **done** Interface with GPS and timing systems (`telemetry-logging`, `lap-timing`)
- **done** Modular software design: separate modules for data acquisition, tune management, user interface and voice assistant
- **todo** Interface with external sensors
- **done** Custom dashboard UI (web, served from the Pi, works offline)
- **todo** Mobile app (iOS/Android, optional)
- **todo** Voice assistant integration (custom or Alexa/Google, optional)
- **planned, separate repo** [Companion app](docs/companion-app.md) for tunes, voice training data and local model updates

## 2. Data Acquisition & Logging — done
- **done** Continuous OBD-II data logging: RPM, speed, throttle and temperatures (`telemetry-logging`). Fuel/air data and ignition timing PIDs are **todo**
- **done** GPS & lap timing integration, synced with ECU logs (`lap-timing`)

## 3. Tune Management — done (ECU backends beyond software are todo)
- **done** "Race" and "Street" profiles (`tune-profiles`)
- **done** Instant switching through one service for voice, dashboard and app (`tune-switching`). Switching is software-only; the GPIO map-switch (`live`) and engine-off flashing (`flash`) backends are **todo**
- **done** Historical tune data: switch history, sessions tagged with the active tune
- **done** User tune & car database: per-car library, save/retrieve/share via export and import (`tune-library`)
- **done** Tune provenance, human approval and protected stock tune (tune safety #1, part 1)
- **done** Analyze live data to **recommend** profiles (`tune-recommendations`). Advisory only: auto-adjusting tunes is excluded until tune safety (#1) is resolved. Historical/ML analysis is **todo**

## 4. Real-Time Feedback & Copilot Interface — partial
- **done** Voice assistant (Jarvis-style): text-to-speech feedback on engine health, performance and tune status (`copilot-feedback`)
- **todo** Respond to user queries and commands
- **done** Dashboard display: live data, lap times, tune status, alerts (`live-dashboard`)

## 5. Manual Override System — todo
- **todo** Physical controls: dedicated override button or switch for manual tune selection
- **todo** Voice command override (e.g. "Jarvis, switch to race mode now")
- **todo** Mobile app/remote access: manual override and tune selection via a **secure** app interface (needs API authentication)

## 6. Safety & Compliance — blocked
- **blocked** Tune validation: ensure street tunes meet legal and safety requirements, and alert the user if a selected tune is not street compliant. Needs tune content decoding (ECU definition / XDF), tracked in tune safety #1. `ComplianceChecker` reports "unknown" until then

## 7. Data Analysis & Reporting — todo
- **todo** Performance reports: post-session reports with lap times, engine stats and tune effectiveness
- **todo** Cloud sync & community sharing (optional). Downloaded tunes must enter as `imported` and need approval

## 8. Extensibility & Future Features — todo
- **partial** Plugin system: third-party modules for new sensors, analytics or UI enhancements (basic registry exists)
- **todo** OTA updates: over-the-air software updates. Tunes are not updated OTA; they go through import and approval
