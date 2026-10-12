# Design

## Context

- Tunes live in each car's `tunes` table (`id, name, data, created_at, notes, deleted_at`). `TuneManager` saves, gets, renames, soft-deletes, exports and imports them. `ProfileManager.assign` and `TuneSwitcher.switch` accept any non-deleted tune.
- Switching is the only path to the ECU, and is software-only today (see `openspec/specs/tune-switching`).
- Future code, including AI tune generation and recommendations, will run in the same process and may write to the same SQLite file. Safeguards therefore need to hold even against code that bypasses `TuneManager`.

## Goals / Non-Goals

**Goals:**
- An unapproved tune can never become active or be assigned, whichever code path is used.
- Approval is bound to the exact bytes reviewed.
- There is always a known-good fallback, reachable from any source.

**Non-Goals:**
- Authenticating approvers. `approved_by` is self-reported until the API gains auth (tracked in #1).
- Validating tune contents (checksums, safety envelope). That is the next safety change.
- Reading the stock image off the ECU. That needs a flash-capable backend. For now the stock image is supplied as a file.

## Decisions

**Columns on `tunes`, not a separate approvals table.** Add `origin TEXT NOT NULL DEFAULT 'human'`, `approved_at`, `approved_by` and `approval_note`. There is only one approval per tune because tune data is immutable, so a side table adds joins for no benefit.

**Migration approves legacy tunes.** When the `origin` column is first added, existing rows get `origin = 'human'` from the default, plus `approved_at = now` and `approved_by = 'migration'`. They were created by a person through `save_tune`, and refusing them would break existing profiles. The `migration` marker keeps this auditable.

**Enforce in the database as well as in Python.** Code that bypasses `TuneManager` (e.g. a future generator writing SQL) cannot get around the rules:
- A `BEFORE UPDATE OF data, origin ON tunes` trigger aborts. This makes data and origin immutable, so a generated tune can't be relabelled `human` and a reviewed tune can't have its bytes swapped.
- A partial unique index on `tunes(origin) WHERE origin = 'stock'` allows only one stock tune per car.
- `TuneSwitcher` and `ProfileManager` check `approved_at IS NOT NULL` themselves too, so refusals carry clear reasons.

**Approval sources.** `APPROVAL_SOURCES = ('dashboard', 'app', 'manual')`. `voice` is excluded because a misheard command or a passenger shouldn't approve an engine tune. `auto` is excluded by definition. `manual` covers a person using the CLI.

**`auto` restriction lives in the switcher.** An `auto` request with a `tune_id` is recorded as a refused switch (not raised as a `ValueError`), so the history shows any attempt by automation to go outside profiles.

**Revert to stock is a switch with `kind = 'revert'`.** It goes through the same `_attempt` path (approval, engine-off gate, backend, history), and a `kind` column added to `tune_switches` (default `switch`) records it. Revert is allowed from every source, including `auto`, because falling back to stock is the safe direction. It is still blocked for `flash` backends while the engine runs.

**Small CLI for human actions.** `python -m tune_management.tune_cli` provides `list`, `import`, `save-stock` and `approve` (source `manual`). Without it the only way to store a stock image or approve a tune is the HTTP API.

## Risks / Trade-offs

- [Self-reported approver name] → Recorded with source and time. Real identity comes with auth before any `live`/`flash` backend ships (#1).
- [Legacy tunes auto-approved by migration] → The `approved_by = 'migration'` marker lets the user review them, and the README says so.
- [A stock tune supplied as a file might not actually be stock] → Out of scope until a backend can read the ECU. The tune is labelled by origin, not verified.
