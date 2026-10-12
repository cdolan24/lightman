# Spec Delta

## Purpose

Lets the driver select a driving profile or fall back to the stock tune with a physical control on the Pi, without a screen or voice.

## ADDED Requirements

### Requirement: Button short press toggles profile
In button mode, a short press SHALL switch to `race` when the active profile is `street`, and to `street` in every other case (race, a tune selected directly, stock, or nothing active).

#### Scenario: Street to race
- **WHEN** street is active and the button is pressed briefly
- **THEN** a switch to the race profile is requested

#### Scenario: From stock
- **WHEN** the stock tune is active and the button is pressed briefly
- **THEN** a switch to the street profile is requested

### Requirement: Button long press reverts to stock
In button mode, holding the button for at least the long-press time (default 2 s) SHALL request a revert to the stock tune, and SHALL NOT also perform the short-press toggle.

#### Scenario: Hold
- **WHEN** the button is held for 2.5 s
- **THEN** a revert to stock is requested and no profile toggle happens

### Requirement: Toggle switch selects profile
In switch mode, the switch being on SHALL select `race` and off SHALL select `street`. The selection SHALL be requested when the position changes and once at startup.

#### Scenario: Flip on
- **WHEN** the switch is turned on
- **THEN** a switch to the race profile is requested

#### Scenario: Startup position
- **WHEN** the service starts with the switch off
- **THEN** a switch to the street profile is requested

### Requirement: Same safety path as every switch
Override actions SHALL go through the tune switcher with source `manual`, so approval, engine-off, history, and refusal rules apply unchanged.

#### Scenario: Unassigned profile
- **WHEN** the button requests race but no tune is assigned to race
- **THEN** the switch is refused and recorded in the history with source `manual`

### Requirement: Optional and fault-tolerant
The override SHALL be disabled unless a GPIO pin is configured. If the GPIO library is unavailable or the pin cannot be used, the override SHALL be disabled with a logged message and the rest of the service SHALL keep running.

#### Scenario: Not on a Pi
- **WHEN** a pin is configured but no GPIO library is available
- **THEN** the service runs without the override and logs that it is disabled
