# tune-profiles Specification

## Purpose
Gives each car named driving profiles (Race and Street) that point at tunes in its library, so a mode can be selected by name instead of by tune.

## Requirements

### Requirement: Default profiles
Every car SHALL have a `race` profile and a `street` profile, which start with no tune assigned.

#### Scenario: New car
- **WHEN** profiles are listed for a car that has never been configured
- **THEN** `race` and `street` are returned, each with no tune

### Requirement: Assign a tune to a profile
The system SHALL allow assigning any tune from the car's own library to a profile, replacing any previous assignment.

#### Scenario: Assign
- **WHEN** tune "Track Day" is assigned to the race profile
- **THEN** the race profile reports "Track Day" as its tune

#### Scenario: Tune from another car
- **WHEN** a tune id that is not in this car's library is assigned
- **THEN** the assignment is refused and the profile is unchanged

### Requirement: Profile names
Profile names SHALL be case-insensitive. Referencing a profile that does not exist SHALL be reported as an error.

#### Scenario: Mixed case
- **WHEN** a switch to "Race" is requested
- **THEN** it resolves to the `race` profile

#### Scenario: Unknown profile
- **WHEN** a switch to profile "qualifying" is requested
- **THEN** the system reports the profile as unknown
