# Proposal

## Why

Section 4 of the plan calls for a Jarvis-style copilot that speaks feedback on engine health, performance and tune status. Lightman now logs telemetry and laps, switches tunes and produces recommendations, but it never tells the driver anything. The driver can't look at a screen on track, so spoken feedback is the main way Lightman's data reaches them. This change adds the feedback side. Understanding voice commands is a separate change because it needs a speech-recognition decision.

## What Changes

- **Announcer:** a non-blocking speech queue in front of text-to-speech.
  - Warnings are spoken before routine messages.
  - Messages that waited too long are dropped rather than spoken late.
  - Duplicate pending messages are collapsed.
  - A speech failure never crashes the caller.
- **Feedback monitor:** watches the car's database (the latest session's samples and laps, recommendations, and switch history) and announces:
  - **Engine-health alerts:**
    - Critical coolant temperature, with hysteresis and a repeat cooldown.
    - Low fuel.
    - Loss of OBD-II data during a session.
  - **Lap completions,** with the lap time and whether it's the session best.
  - **New recommendations,** once when they first appear (not repeated while they persist).
  - **Tune switch results** from non-voice sources, stating honestly when a switch was software-only and refusal reasons. Voice-initiated switches are answered by the voice command handler instead.
- Alert thresholds have defaults and can be overridden.

## Capabilities

### New Capabilities
- `copilot-feedback`: Spoken, prioritized announcements of engine-health alerts, laps, recommendations and tune switches.

### Modified Capabilities
None.

## Impact

- New: `voice_assistant/announcer.py`, `voice_assistant/feedback_monitor.py`, with tests. `VoiceAssistant` remains the text-to-speech backend.
- Reads the existing tables. No schema changes and no new dependencies.
- Out of scope: speech recognition and voice commands (next change), the web dashboard, and the main Lightman service that runs the monitor alongside the logger (it will host this monitor).
