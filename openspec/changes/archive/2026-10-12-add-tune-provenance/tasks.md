# Tasks

## 1. Schema

- [x] 1.1 Add `origin`, `approved_at`, `approved_by` and `approval_note` to `tunes` (approving legacy rows as `migration`), a `kind` column to `tune_switches`, the data/origin immutability trigger, and the single-stock partial unique index. Verify with tests that migrated tunes are approved by `migration`, that a raw SQL update of `data` or `origin` aborts, and that a second stock row is rejected

## 2. Library

- [x] 2.1 Add an `origin` parameter to `save_tune` (human and stock auto-approved; imported and generated unapproved), make `import_tune` always `imported`, add `save_stock_tune` / `get_stock_tune`, `approve_tune(tune_id, approved_by, source, note)` with the approval source rules, refuse stock deletion, and expose origin/approval in `list_tunes` / `get_tune`. Verify with tests for each `tune-library` scenario in this change

## 3. Profiles and switching

- [x] 3.1 Refuse assignment of unapproved tunes in `ProfileManager.assign`. Verify with a test for the unapproved-tune scenario
- [x] 3.2 Refuse unapproved tunes and `auto` + `tune_id` in `TuneSwitcher`, and add `revert_to_stock(source)` recorded with `kind = 'revert'`. Verify with tests for each new `tune-switching` scenario (except HTTP), using a flash backend for the engine-running case

## 4. Interfaces and docs

- [x] 4.1 Add origin/approval fields to `GET /tunes`, and add `POST /tunes/<id>/approve` (403 on a refused source or missing name, 404 on an unknown tune) and `POST /revert`. Verify with Flask test-client tests for approve, auto-approve refusal and revert
- [x] 4.2 Add `tune_management/tune_cli.py` (`list`, `import`, `save-stock`, `approve`). Verify with a test that runs `main([...])` to import, approve and list a tune
- [x] 4.3 Update `README.md` (origins, approval, stock/revert, CLI, new endpoints, migration note) and `docs/open-issues/tune-safety.md` (mark provenance/approval, `auto` restriction and protected stock/revert as addressed; the rest stays open). Verify that the documented endpoints and CLI commands match the code

## 5. Integration check

- [x] 5.1 Run `pytest data_acquisition tune_management user_interface` and `openspec validate add-tune-provenance --strict`, and confirm both pass
