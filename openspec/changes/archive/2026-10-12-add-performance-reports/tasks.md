# Tasks

## 1. Recording

- [x] 1.1 Add `laps.tune_id` and `sessions.lap_line` (JSON text) with migration, have `DataLogger` store the lap line at session start and the active tune (from `car_state`) on each lap. Verify with tests for the tune-changed-mid-session and line-recorded scenarios, and that sessions without lap timing store no line

## 2. Reports

- [x] 2.1 Rewrite `tune_management/performance_report.py`: `list_sessions`, `session_report` (laps, best/average/stdev, engine stats, `SessionNotFound`) and `tune_comparison` (grouped by line, then tune). Verify with tests for every `performance-reports` scenario except the interfaces
- [x] 2.2 Add the CLI (`--car-id`, `--session`, `--compare`, default list) with readable lap times, and the HTTP routes `GET /sessions`, `GET /sessions/<sid>/report` (404 when unknown) and `GET /tune-comparison`. Verify with CLI output tests and Flask test-client tests

## 3. Docs

- [x] 3.1 Document reports (CLI, endpoints, which laps are compared) in `README.md`, and update Section 7 in `copilot_implementation_plan.md`. Verify that the documented routes match the URL map

## 4. Integration check

- [x] 4.1 Run `pytest` and `openspec validate add-performance-reports --strict`, and confirm both pass
