# Tasks

## 1. Announcer

- [x] 1.1 Implement `voice_assistant/announcer.py`: `Announcer(speak, clock, start=True)` with `say(text, priority)`, priority ordering, expiry, de-duplication, a background worker, `drain()` and `stop()`, and logged speech errors. Verify with tests for ordering, staleness, de-duplication, error isolation, and a threaded test where `say()` returns immediately while `speak` blocks

## 2. Feedback monitor

- [x] 2.1 Implement `voice_assistant/feedback_monitor.py`: `FeedbackMonitor(car_id, announcer, limits, recommender, clock)` with `check()` and `run(interval, stop_event)`, covering the coolant, fuel and OBD-loss alerts, laps, recommendations and switches, plus the lap-time wording helper. Verify with tests for every `copilot-feedback` scenario except the announcer ones, using a recording announcer and a fake clock

## 3. Docs

- [x] 3.1 Document spoken feedback (what is announced, the default limits, how to run the monitor) in `README.md`, and update Section 4 status in `copilot_implementation_plan.md`. Verify that the documented defaults match `DEFAULT_LIMITS`

## 4. Integration check

- [x] 4.1 Run `pytest` and `openspec validate add-copilot-feedback --strict`, and confirm both pass
