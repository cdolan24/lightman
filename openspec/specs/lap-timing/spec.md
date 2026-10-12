# lap-timing Specification

## Purpose
Times laps on a circuit by detecting when the car crosses a configured start/finish line, so lap times can be synchronized with logged engine data.

## Requirements

### Requirement: Start/finish line definition
The system SHALL accept a start/finish line defined by two GPS coordinates (latitude/longitude endpoints).

#### Scenario: Configure a line
- **WHEN** a session is started with a start/finish line
- **THEN** lap timing is active for that session

#### Scenario: No line configured
- **WHEN** a session is started without a start/finish line
- **THEN** no laps are recorded and samples have no lap number

### Requirement: Crossing detection
The system SHALL detect a crossing when the path between two consecutive GPS fixes intersects the start/finish line, and SHALL estimate the crossing time by interpolating between the two fixes.

#### Scenario: Crossing between fixes
- **WHEN** one fix is 10 m before the line at t=0 s and the next is 10 m past it at t=1 s
- **THEN** a crossing is detected at approximately t=0.5 s

#### Scenario: Path does not reach the line
- **WHEN** consecutive fixes pass beside the line's endpoints without intersecting it
- **THEN** no crossing is detected

### Requirement: Lap recording
The first crossing in a session SHALL start lap 1. Each subsequent crossing SHALL complete the current lap, store its lap number, start time, end time, and duration, and start the next lap.

#### Scenario: Two completed laps
- **WHEN** the car crosses the line three times at t=10 s, t=100 s, and t=185 s
- **THEN** lap 1 is stored with duration 90 s and lap 2 with duration 85 s

### Requirement: Minimum lap time debounce
The system SHALL ignore crossings that occur less than a configurable minimum lap time (default 10 s) after the previous crossing.

#### Scenario: GPS jitter at the line
- **WHEN** a second crossing is detected 2 s after the first
- **THEN** it is ignored and lap 1 continues

### Requirement: Lap tagging of samples
Each telemetry sample taken while a lap is in progress SHALL record the current lap number; samples before the first crossing SHALL have no lap number.

#### Scenario: Out-lap samples
- **WHEN** samples are taken before the first crossing
- **THEN** their lap number is null
