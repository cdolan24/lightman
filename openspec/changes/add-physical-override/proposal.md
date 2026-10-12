# Proposal

## Why

Section 5 of the plan calls for a dedicated physical override button or switch for manual tune selection. On track the driver can't use a phone, and voice commands aren't built yet. A physical control is the most reliable way to change profile or fall back to stock. The existing `ManualOverride` class only holds in-memory flags that nothing reads, so it doesn't actually switch anything.

## What Changes

- Add a physical override control on one of the Pi's GPIO pins (wired to the Pi, not the ECU, so Lightman stays plug-and-play). It supports two modes:
  - **Button:** a short press toggles the profile. From `street` it goes to `race`; from anything else it goes to `street`, so the default direction is the safer one. A long press (default 2 s) reverts to the stock tune.
  - **Toggle switch:** the switch position selects the profile (on = `race`, off = `street`). It is applied when the position changes and once at startup.
- Every action goes through the tune switcher with source `manual`, so all existing safety rules (approval, engine-off for flash) and switch history apply. The spoken feedback monitor already announces the result.
- Configuration: `[override] pin` (BCM numbering; -1 = disabled, the default), `mode` (`button` or `switch`) and `long_press` seconds. If the GPIO library is unavailable or the pin can't be claimed, only the override is disabled (logged).
- Remove the unused in-memory `ManualOverride` class.
- The installer adds the Pi's GPIO packages (`python3-gpiozero`, `python3-lgpio`; Pi 5 needs lgpio) and creates the virtualenv with access to system packages so they're usable.

## Capabilities

### New Capabilities
- `manual-override`: The physical button or switch for selecting profiles and reverting to stock.

### Modified Capabilities
- `lightman-service`: adds the optional override control to the configuration and startup.

## Impact

- New: `tune_management/override_control.py`, with tests (using gpiozero's mock pins). `gpiozero` is added to `requirements-dev.txt` for tests. On the Pi it comes from the OS packages.
- Modified: `lightman/config.py`, `lightman/service.py`, `lightman.example.toml`, `deploy/install.sh`, README.
- Removed: `tune_management/manual_override.py` (unused).
- Out of scope: voice command override (needs the speech-recognition decision), mobile app override (needs authentication), and an "override hold" that locks out automatic switching (nothing switches automatically yet).
