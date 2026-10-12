# Spec Delta

## Purpose

Suggests which driving profile suits the car's current conditions, based on live telemetry and the active profile, so the driver can decide whether to switch. Recommendations never change the tune themselves.

## ADDED Requirements

### Requirement: Advisory only
Producing recommendations SHALL NOT change the active tune or profile, SHALL NOT create, modify, or approve any tune, and SHALL NOT record a switch.

#### Scenario: Recommendation leaves state alone
- **WHEN** recommendations suggest switching from race to street
- **THEN** the active tune, profiles, tune library, and switch history are unchanged

### Requirement: Recommendation contents
Each recommendation SHALL include a rule identifier, a severity (`info` or `warning`), the suggested profile (or none), a human-readable reason, and the telemetry values it was based on.

#### Scenario: Contents
- **WHEN** a recommendation is produced because coolant is 112 °C
- **THEN** it has a rule id, severity `warning`, suggested profile `street`, a reason mentioning the coolant temperature, and the value 112

### Requirement: Live data required
Recommendations SHALL be based on the most recent sample of the car's latest logging session. If that sample is older than a freshness limit (default 10 s), or there is no session, the system SHALL return no recommendations.

#### Scenario: Stale data
- **WHEN** the newest sample is 60 s old
- **THEN** no recommendations are returned

#### Scenario: Missing readings
- **WHEN** the newest sample has a null coolant temperature
- **THEN** rules that need coolant temperature produce nothing

### Requirement: Overheating on race
When the active profile is `race` and coolant temperature is at or above the hot limit (default 105 °C), the system SHALL recommend `street` with severity `warning`.

#### Scenario: Hot engine
- **WHEN** race is active and coolant reads 108 °C
- **THEN** a `warning` recommending `street` is returned

#### Scenario: Already on street
- **WHEN** street is active and coolant reads 108 °C
- **THEN** no profile-change recommendation for overheating is returned

### Requirement: Heat-soaked intake on race
When the active profile is `race` and intake air temperature is at or above the heat-soak limit (default 60 °C), the system SHALL recommend `street` with severity `warning`.

#### Scenario: Heat soak
- **WHEN** race is active and intake air reads 65 °C
- **THEN** a `warning` recommending `street` is returned

### Requirement: Cold engine on race
When the active profile is `race` and coolant temperature is below the warm-up limit (default 70 °C), the system SHALL recommend `street` with severity `info` until the engine is warm.

#### Scenario: Cold start
- **WHEN** race is active and coolant reads 40 °C
- **THEN** an `info` recommendation for `street` is returned

### Requirement: On track on street
When the active profile is `street`, the current session has recorded at least one lap crossing, and coolant and intake air are both readable and inside their normal limits, the system SHALL recommend `race` with severity `info`.

#### Scenario: Track session on street
- **WHEN** street is active, the session is on lap 2, coolant reads 90 °C and intake air reads 35 °C
- **THEN** an `info` recommendation for `race` is returned

#### Scenario: Track session but hot
- **WHEN** street is active on a timed lap and coolant reads 108 °C
- **THEN** no `race` recommendation is returned

### Requirement: Configurable thresholds
The hot, heat-soak, warm-up, and freshness limits SHALL be overridable; unspecified limits SHALL use the defaults.

#### Scenario: Lower hot limit
- **WHEN** the hot limit is set to 100 °C, race is active, and coolant reads 102 °C
- **THEN** a `warning` recommending `street` is returned

### Requirement: HTTP recommendations
The HTTP interface SHALL return the car's current recommendations as a list, which is empty when there are none.

#### Scenario: Fetch
- **WHEN** a client requests recommendations for a car whose race tune is active and whose engine is overheating
- **THEN** the response lists the overheating recommendation
