# Proposal

## Why

Section 4 of the plan calls for a dashboard display showing live data, lap times, tune status and alerts. The Pi already serves an HTTP API, but there is no page to look at. The only live-data endpoint (`/api/obd`) also queries the OBD-II adapter directly, which would compete with the data logger for the same serial adapter.

## What Changes

- Add `GET /api/cars/<id>/live`. It returns the in-progress session, its latest sample (with the sample's age), and the session's laps with the best lap marked. It reads from the database, so the logger stays the only process talking to the adapter.
- Serve a single-page dashboard at `/` (`/?car=<id>`, default car 1). It shows:
  - Large live readouts: rpm, speed, coolant, intake, throttle, fuel.
  - Lap timing: current lap, last lap, best lap, and the lap list.
  - Active tune and profile, with the honest switch method.
  - Current recommendations and the latest switch results.
  - Buttons for the race and street profiles and **revert to stock**, sent with source `dashboard`.
- The page is self-contained (no CDN or internet access needed in the car), dark, readable at a glance, and works on a phone. It polls about once a second and shows clearly when data is stale or no session is running.
- Tune approval stays out of the in-car dashboard on purpose. It is a deliberate review task for the companion app or CLI.

## Capabilities

### New Capabilities
- `live-dashboard`: The live session endpoint and the in-car dashboard page.

### Modified Capabilities
None.

## Impact

- New: `user_interface/static/dashboard.html`, plus the `live` route in `user_interface/api.py`. `dashboard.py` serves the page.
- No new dependencies.
- Out of scope: authentication (tracked in #1, required before `live`/`flash` backends), charts and history views (companion app / reports), and the combined Lightman service.
