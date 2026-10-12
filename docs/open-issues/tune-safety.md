# Open issue: Tune safety safeguards

**Status:** Open. This must be resolved before any `live` or `flash` ECU backend ships, and before Lightman generates or recommends tunes.

## Problem

A bad tune can destroy an engine within seconds. Too much ignition advance causes detonation, a lean mixture under boost burns pistons, and overboost or an overrev causes mechanical failure. Tuning is a specialised science. The product goal says Lightman "can generate new ones" (tunes), and a local AI model can produce plausible-looking but dangerous values. The system currently has almost nothing that stops a bad tune from being activated.

## What exists today

- **Switching is software-only.** The `software` ECU backend records the selection and never touches the ECU. This is currently the main safeguard.
- **Engine-off gate.** Any `flash` backend switch is refused unless engine speed reads 0 rpm. It is also refused when rpm cannot be read.
- **Audit trail.** Every switch attempt is recorded with its source (`voice`, `dashboard`, `app`, `manual`, `auto`), including refusals and failures.

## Gaps

1. **No tune content validation.** Any bytes can be saved, imported (`.lmtune`) and activated. Nothing checks image size, ECU/calibration ID or checksums.
2. **No safety envelope.** Nothing compares a tune's maps (timing, AFR/fuel, boost, rev limit, injector duty) against limits or a known-good baseline.
3. **Compliance checker is a stub.** `tune_management/compliance_checker.py` always returns `True`.
4. **No provenance or human approval.** Hand-made, imported and AI-generated tunes are indistinguishable. The `auto` source can activate any tune in the library.
5. **No fallback or rollback.** There is no protected stock tune, no post-flash read-back verification, and no automatic revert.
6. **No post-switch monitoring.** Nothing watches knock, AFR, coolant/oil temperature or EGT after a switch to catch a tune that misbehaves.

## Proposed safeguards (to scope into OpenSpec changes)

- **Tune provenance and approval:** tag each tune as `stock`, `human`, `imported` or `generated`. Generated and imported tunes cannot be activated or assigned to a profile until a human explicitly approves them. Generated tunes are never auto-flashed.
- **Restrict `auto`:** automatic switching (from recommendations) may only choose between human-approved tunes that are already assigned to profiles. It must never create, modify or flash a tune.
- **Image validation:** use per-ECU definitions (e.g. TunerPro XDF + BIN size and checksum rules) to validate size, calibration ID and checksums before saving or flashing.
- **Safety envelope:** decode the key maps using the ECU definition and reject tunes that exceed configured limits or deviate from the stock/baseline tune by more than a set threshold, unless a human overrides with a recorded reason.
- **Protected stock tune and rollback:** always keep the stock image, make it undeletable, and provide a one-step "revert to stock". Verify each flash by reading it back.
- **Post-switch watchdog:** after a switch, monitor knock retard, AFR, temperatures and boost (where the ECU or sensors expose them). Alert by voice, and if a `live` backend allows it, revert to the previous tune.
- **Recommendations are advisory:** the upcoming recommendations change produces suggestions only, which a human applies.
- **Testing:** test with a bench simulator/emulator before in-car testing, and keep a log of which tunes have been proven on the car.

## Related

- Specs: `openspec/specs/tune-switching`, `openspec/specs/tune-library`
- Code: `tune_management/tune_switcher.py` (engine-off gate), `tune_management/ecu_backend.py`, `tune_management/compliance_checker.py`
