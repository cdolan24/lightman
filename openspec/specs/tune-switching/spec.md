# tune-switching Specification

## Purpose
Provides the single way to change a car's active tune, used by voice, dashboard, app, and manual controls. It applies the change through the car's ECU backend, enforces safety rules, and keeps a history of every switch.

## Requirements

### Requirement: Switch by profile or tune
The system SHALL activate a car's tune either by profile name or by tune id, and SHALL persist the active tune and profile so they survive a restart.

#### Scenario: Switch to race
- **WHEN** a switch to the race profile is requested and it has a tune assigned
- **THEN** that tune becomes the car's active tune, the active profile is `race`, and both are still reported after a restart

#### Scenario: Switch directly to a tune
- **WHEN** a switch to a specific tune id is requested
- **THEN** that tune becomes active and the active profile is cleared

#### Scenario: Profile without a tune
- **WHEN** a switch to a profile with no tune assigned is requested
- **THEN** the switch is refused and the active tune is unchanged

### Requirement: Switch source
Every switch request SHALL state its source, one of `voice`, `dashboard`, `app`, `manual`, or `auto`.

#### Scenario: Source recorded
- **WHEN** the dashboard requests a switch
- **THEN** the switch history entry records source `dashboard`

### Requirement: ECU backend application
The system SHALL apply each switch through the car's configured ECU backend. Each backend SHALL declare its method (`software`, `live`, or `flash`), and that method SHALL be reported with every switch result. The default backend SHALL be `software`, which only records the selection and does not communicate with the ECU.

#### Scenario: Default backend
- **WHEN** a switch succeeds on a car with no backend configured
- **THEN** the result reports method `software`

#### Scenario: Backend failure
- **WHEN** the backend reports an error while applying a tune
- **THEN** the switch fails, the active tune is unchanged, and the error is returned

### Requirement: Engine-off gate for flashing
A switch whose backend method is `flash` SHALL only proceed when the engine is confirmed off (engine speed reads 0 rpm). If the engine is running or engine speed cannot be read, the switch SHALL be refused.

#### Scenario: Engine running
- **WHEN** a flash switch is requested while engine speed reads 850 rpm
- **THEN** the switch is refused with a reason stating the engine must be off

#### Scenario: Engine speed unknown
- **WHEN** a flash switch is requested and engine speed cannot be read
- **THEN** the switch is refused

#### Scenario: Engine off
- **WHEN** a flash switch is requested while engine speed reads 0 rpm
- **THEN** the backend applies the tune

### Requirement: Switch history
The system SHALL record every switch attempt with its time, source, requested profile or tune, the previous and new tune, the method, whether it succeeded, and the reason for any refusal or failure.

#### Scenario: Refused switch is recorded
- **WHEN** a switch is refused
- **THEN** the history contains an entry marked unsuccessful with the refusal reason

### Requirement: Sessions default to the active tune
A logging session started without an explicit tune SHALL be tagged with the car's active tune, if any.

#### Scenario: Active tune tagging
- **WHEN** the race tune is active and a logging session is started without a tune id
- **THEN** the session is recorded with the race tune's id

### Requirement: HTTP control
The system SHALL expose HTTP endpoints to list a car's tunes and profiles, assign a tune to a profile, read the active tune, request a switch, and read the switch history. Refused or failed switches SHALL return an error status with the reason.

#### Scenario: Dashboard switch
- **WHEN** a client posts a switch to profile `street` for car 1
- **THEN** the response reports success, the active tune, and the method

#### Scenario: Refused over HTTP
- **WHEN** a client requests a switch to a profile with no tune
- **THEN** the response has an error status and the refusal reason
