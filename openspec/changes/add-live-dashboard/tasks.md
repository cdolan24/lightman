# Tasks

## 1. Live endpoint

- [x] 1.1 Add `GET /api/cars/<id>/live` (open session, latest sample with `age_seconds`, laps, `best_lap`). Verify with Flask test-client tests for a running session, no session, and that no OBD query is made

## 2. Dashboard page

- [x] 2.1 Add `user_interface/static/dashboard.html`: readouts, laps, tune status, recommendations, history, race/street/revert buttons with source `dashboard`, and stale/no-session indicators, polling every second with no external resources. Serve it at `/` from `dashboard.py`. Verify with tests that `/` returns the page, that it contains no `http://` or `https://` resource references, and that the API paths it calls exist in the app's URL map
- [x] 2.2 Run the dashboard against a simulated session (scripted samples, laps and switches written to a temp DB) and check the page in a browser. Verify that readings, laps, the tune status and a refused switch display correctly

## 3. Docs

- [x] 3.1 Document the dashboard and `/live` in `README.md`, and update Section 4 status in `copilot_implementation_plan.md`. Verify that the README endpoint table matches the URL map

## 4. Integration check

- [x] 4.1 Run `pytest` and `openspec validate add-live-dashboard --strict`, and confirm both pass
