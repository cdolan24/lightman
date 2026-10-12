# Tasks

## 1. Override logic

- [x] 1.1 Implement `tune_management/override_control.py`: `OverrideControl(switcher)` with `short_press()`, `long_press()` and `set_switch(on)`, using source `manual`, plus `attach_gpio(control, pin, mode, long_press, pin_factory=None)` binding gpiozero `Button` events (`when_held` for long press, release without hold for short press) and returning the device. Verify with tests for every `manual-override` scenario, using gpiozero's `MockFactory` pins for the hardware binding (add `gpiozero` to `requirements-dev.txt`)

## 2. Service and config

- [x] 2.1 Add `[override] pin`/`mode`/`long_press` to `DEFAULTS` with validation, start the override in `LightmanService` (degrading on import or pin errors), update `lightman.example.toml`, and remove `tune_management/manual_override.py`. Verify with config tests, and with service tests for configured (mock pins), default (none) and unavailable-GPIO cases

## 3. Deployment and docs

- [x] 3.1 Update `deploy/install.sh` (apt `python3-gpiozero python3-lgpio`, venv with `--system-site-packages`), the README (wiring: button between the GPIO pin and GND, internal pull-up; modes; config rows) and `copilot_implementation_plan.md`. Verify that `bash -n` passes and that every `DEFAULTS` key appears in the README

## 4. Integration check

- [x] 4.1 Run `pytest` and `openspec validate add-physical-override --strict`, and confirm both pass
