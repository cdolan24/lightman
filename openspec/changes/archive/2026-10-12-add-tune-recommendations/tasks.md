# Tasks

## 1. Recommender

- [x] 1.1 Implement `tune_management/recommender.py`: a `Recommendation` dataclass, `Recommender(car_id, limits=None, clock=None)` and `recommend()`. It reads the latest sample of the latest session (null-safe, with a freshness check against the sample's `wall_time`), the active profile from `car_state`, and the current lap from the sample, then applies the four rules. Verify with tests for every `tune-recommendations` scenario except HTTP, including a test that state, the tune library and switch history are unchanged after `recommend()`

## 2. Interfaces and docs

- [x] 2.1 Add `GET /api/cars/<id>/recommendations` and verify it with a Flask test-client test for the overheating scenario and an empty list
- [x] 2.2 Document the rules, default limits, advisory-only behaviour and endpoint in `README.md`, and mark the Section 3 recommendation item done in `copilot_implementation_plan.md`. Verify that the documented defaults match `DEFAULT_LIMITS`

## 3. Integration check

- [x] 3.1 Run `pytest` and `openspec validate add-tune-recommendations --strict`, and confirm both pass
