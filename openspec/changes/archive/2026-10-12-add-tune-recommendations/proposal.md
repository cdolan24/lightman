# Proposal

## Why

The last item in Section 3 of the plan is to "analyze logged data to recommend or auto-adjust tunes". Tune safety (#1) rules out auto-adjusting: Lightman must not change tunes on its own judgment. What's still useful is advisory recommendations. For example, Lightman can notice that the engine is running hot on the race profile and suggest switching to street, and the voice assistant and dashboard (Section 4) can present that to the driver.

## What Changes

- Add a recommender that looks at the car's live telemetry (the latest sample of the current logging session) and the active profile, and returns recommendations. Each one has a suggested profile (if any), a severity and a human-readable reason with the values behind it.
- Initial rules:
  - Engine running hot (coolant) on `race` → suggest `street`.
  - Intake air heat-soaked on `race` → suggest `street`.
  - Engine still cold on `race` → suggest `street` until it warms up.
  - Lap timing active, engine healthy, on `street` → suggest `race`.
- Recommendations are **advisory only**. Producing one never changes the active tune, and no tune is ever created or modified.
- Thresholds have safe defaults and can be overridden per recommender (the companion app will configure them later).
- New HTTP endpoint `GET /api/cars/<id>/recommendations`.

## Capabilities

### New Capabilities
- `tune-recommendations`: Advisory profile suggestions derived from live telemetry and the active profile.

### Modified Capabilities
None.

## Impact

- New: `tune_management/recommender.py` and tests. `user_interface/api.py` gains one route.
- Reads the `samples`, `sessions`, `laps` and `car_state` tables. No schema changes.
- Out of scope: automatic switching on recommendations, tune generation or modification, spoken delivery (Section 4), and a trend/ML analysis of historical sessions (later, once there is real data).
