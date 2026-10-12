# Proposal

## Why

Tune safety is an open issue (GitHub #1, `docs/open-issues/tune-safety.md`). Lightman is meant to generate tunes eventually, and tunes can be imported from anyone. Today every tune in the library can be activated by any source, including `auto`, and there is no guaranteed safe tune to fall back to. This change adds the two safeguards that matter most before any recommendation or automatic switching exists: a human must approve any tune they didn't make themselves, and every car can keep a protected stock tune that it can always revert to.

## What Changes

- Record each tune's **origin**: `stock`, `human`, `imported`, or `generated`.
- Human-made and stock tunes are approved when saved. **Imported and generated tunes start unapproved** and must be explicitly approved by a named person through a human interface (dashboard, app, or manual). They can never be approved by `voice` or `auto`.
- Tune data becomes immutable: changing a tune means saving a new tune, so an approval always covers exactly the bytes that were reviewed.
- Unapproved tunes cannot be assigned to a profile or activated.
- The `auto` source may only switch by profile (to tunes a human already approved and assigned), never to an arbitrary tune id.
- Each car can store one **stock tune**, which cannot be deleted. **Revert to stock** is available from every source and goes through the same safety gates (engine-off for flash).
- HTTP: tune listings show origin and approval, and new endpoints approve a tune and revert to stock.
- Existing tunes are migrated as `human` and approved, with `approved_by` set to `migration`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `tune-library`: adds tune origin, approval, immutable data, and the stock tune. Stock tunes cannot be deleted. Imported tunes start unapproved.
- `tune-profiles`: only approved tunes can be assigned.
- `tune-switching`: activation requires approval, `auto` is restricted to profiles, and revert to stock is added.

## Impact

- Modified: `tune_management/car_database.py` (new `tunes` columns and migration), `tune_manager.py`, `profiles.py`, `tune_switcher.py`, `user_interface/api.py`, `README.md`, `docs/open-issues/tune-safety.md` (mark which items are addressed).
- No new dependencies.
- **BREAKING (minor):** `import_tune` now returns an unapproved tune, so an imported tune must be approved before it can be assigned or activated.
- Out of scope (stays open in #1): image/checksum validation, safety-envelope limits, flash read-back, the post-switch watchdog, and authentication for approvals (the `approved_by` name is self-reported until the API gains auth).
