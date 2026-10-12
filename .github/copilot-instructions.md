# Copilot instructions for Lightman

- Lightman is Python software for a Raspberry Pi 5 that is plugged into a car's OBD-II port. Keep it drag-and-drop: Pi runtime dependencies go in `requirements.txt`, and dev-only tools go in `requirements-dev.txt`. Desktop tooling belongs in the separate [companion app](../docs/companion-app.md).
- Plan work with OpenSpec: current behaviour is in `openspec/specs/`, and changes are proposed under `openspec/changes/`. The roadmap and its status are in `copilot_implementation_plan.md`.
- Run tests with `pytest`. Tests that need real hardware are marked `@pytest.mark.hardware` and skipped by default.
- Tune safety rules (see `docs/open-issues/tune-safety.md`):
  - Change the active tune only through `TuneSwitcher`.
  - Never approve tunes from `voice` or `auto`. Never bypass the engine-off gate for flashing.
  - Never edit tune data in place; save a new tune instead.
  - Placeholder code must raise `NotImplementedError` or report "unknown", never fake success.
