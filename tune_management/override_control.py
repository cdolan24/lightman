# override_control.py

"""Physical override: a button or toggle switch on a Pi GPIO pin (wired to the Pi, not the ECU)."""

import logging

log = logging.getLogger(__name__)

MODES = ('button', 'switch')

class OverrideControl:
    """What the physical control does. Every action is a normal 'manual' switch, so all safety rules apply."""

    def __init__(self, switcher):
        self.switcher = switcher

    def short_press(self):
        # Street goes up to race; everything else (race, a direct tune, stock, nothing) goes to street.
        target = 'race' if self.switcher.active()['profile'] == 'street' else 'street'
        return self._log(self.switcher.switch('manual', profile=target))

    def long_press(self):
        return self._log(self.switcher.revert_to_stock('manual'))

    def set_switch(self, on):
        return self._log(self.switcher.switch('manual', profile='race' if on else 'street'))

    @staticmethod
    def _log(result):
        if result.ok:
            log.info("Override: tune %s active (%s)", result.active_tune_id, result.method)
        else:
            log.warning("Override refused: %s", result.reason)
        return result

def attach_gpio(control, pin, mode='button', long_press=2.0, pin_factory=None):
    """Bind control to a GPIO pin (BCM numbering, wired to GND with the internal pull-up). Returns the device.

    Raises ImportError without gpiozero, or gpiozero errors if the pin can't be used.
    """
    from gpiozero import Button

    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if mode == 'button':
        device = Button(pin, pull_up=True, bounce_time=0.05, hold_time=long_press, pin_factory=pin_factory)
        held = {'flag': False}
        def on_held():
            held['flag'] = True
            control.long_press()
        def on_released():
            if not held['flag']:
                control.short_press()
            held['flag'] = False
        device.when_held = on_held
        device.when_released = on_released
    else:
        device = Button(pin, pull_up=True, bounce_time=0.1, pin_factory=pin_factory)
        device.when_pressed = lambda: control.set_switch(True)
        device.when_released = lambda: control.set_switch(False)
        control.set_switch(device.is_pressed)   # apply the position the switch is already in
    return device
