# Companion App (separate project)

**Status:** Planned. It will **not** be built in this repository.

## Why a separate app

Tuning is an advanced science. The work that needs care, screen space and expertise belongs on a laptop or desktop, not on a Raspberry Pi in a car: authoring and reviewing tunes, validating them, approving them, curating voice training data and updating the local model. Keeping that work out of this repository means Lightman stays **drag-and-drop software for the Pi**. You copy it on, install `requirements.txt`, and it runs, with no desktop tooling, GUI frameworks or tuning-software dependencies on the Pi.

## Responsibilities

| Companion app (computer) | Lightman (Pi, this repo) |
| --- | --- |
| Load and author tunes (e.g. alongside TunerPro RT and XDF definitions) | Stores tunes and enforces approval, immutability and the stock tune |
| Validate tunes before they reach the car: checksums, ECU/calibration match, safety-envelope diffs against stock | Refuses unapproved tunes, gates flashing on engine-off, keeps switch history |
| Approve tunes (with real user identity once auth exists) | Records approvals; never self-approves (`voice`/`auto` can't approve) |
| Manage voice training data: record, label and prune it, then push it to the Pi | Uses the voice data for recognition |
| Update the local model: build or select it, then push it to the Pi | Runs the local model |
| Configure the Pi: car ids, start/finish lines, ECU backend, alert thresholds | Reads its configuration; works with defaults when nothing is configured |
| Review sessions, laps and reports in depth | Logs sessions; basic reports and live dashboard |
| Push software updates (OTA) | Applies updates |

## Interface to the Pi

The companion app talks to Lightman over the Pi's HTTP API (`user_interface/api.py`). The API has to grow to support it. Each item below becomes a Pi-side OpenSpec change in this repo when the companion app work starts:

- **Authentication** (prerequisite). Approvals and uploads must be tied to a real user. This is also required by the tune safety issue (#1) before any `live`/`flash` backend.
- Tune upload and download. Uploaded tunes enter as `imported` or `generated` and still require approval.
- Voice training data and local model upload, with versioning and rollback to the previous model.
- Configuration read/write.
- Session, lap and sample export.

## Open questions

- Platform and framework. TunerPro RT is Windows-only, which suggests a Windows-first desktop app.
- Transport: Wi-Fi to the Pi's network, USB, or both.
- Repository name and location.
