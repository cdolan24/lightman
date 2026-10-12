# Design

## Context

- `VoiceAssistant.speak()` wraps pyttsx3 and blocks until speech finishes. On the Pi it uses espeak.
- The data logger writes samples and laps into the car's SQLite database. The tune switcher writes `car_state` and `tune_switches`. The recommender reads live samples.
- There is no main Lightman process yet. The logger, dashboard and (later) voice commands will be composed into one service in a later change.

## Goals / Non-Goals

**Goals:**
- Feedback works no matter which process wrote the data. The logger, dashboard and switcher don't need to know the monitor exists.
- Driving-relevant speech is never stale or flooded.
- Everything is testable without audio and without threads.

**Non-Goals:**
- Speech recognition and commands.
- Configurable voices or languages.

## Decisions

**The database is the event source, and the monitor polls it.** `FeedbackMonitor.check()` reads anything new since its last check: samples of the in-progress session, `laps.id > last`, `tune_switches.id > last`, and the current recommendations. The alternative was callbacks from the logger and switcher, which would couple every producer to the feedback system and break across processes (the dashboard runs separately today). Polling once a second on a local SQLite file is cheap. On startup the high-water marks for laps and switches are set to the current maximum ids, so old events aren't replayed.

**"During a session" means `sessions.ended_at IS NULL`.** Engine-health alerts only consider the latest session while it is open. A finished session's last sample would otherwise keep re-triggering alerts.

**Alert state machines with hysteresis.** Coolant re-arms only after the temperature drops 5 °C below the limit, or after the repeat interval while it stays high, so a reading hovering around the limit doesn't chatter. Fuel re-arms after rising above the limit. OBD loss requires that the session has had engine data, then N consecutive null-rpm samples.

**Announcer queue with priorities and expiry.** There is one worker thread and a `Condition`-protected list. The next item spoken is the oldest highest-priority one, and items past their maximum age are dropped when dequeued. `drain()` processes the queue synchronously, so tests can run without the thread (`start=False`). Speech exceptions are logged and swallowed, because a TTS failure must not take down monitoring.

**Voice-initiated switches are skipped.** The upcoming voice command handler answers its own commands, so the monitor skips `source = 'voice'` rows to avoid answering twice.

**Honest switch wording.** Software-only switches say "the ECU was not changed", in line with the product principle of honest status.

## Risks / Trade-offs

- [Polling adds up to one interval (1 s) of latency] → Acceptable for spoken feedback. Lap announcements are not time-critical to the millisecond.
- [espeak quality on the Pi] → Unchanged from today. Voice and model choices belong to the companion-app/local-model work.
