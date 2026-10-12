# Spec Delta

## MODIFIED Requirements

### Requirement: Assign a tune to a profile
The system SHALL allow assigning any approved tune from the car's own library to a profile, replacing any previous assignment. Assigning an unapproved tune SHALL be refused.

#### Scenario: Assign
- **WHEN** tune "Track Day" is assigned to the race profile
- **THEN** the race profile reports "Track Day" as its tune

#### Scenario: Tune from another car
- **WHEN** a tune id that is not in this car's library is assigned
- **THEN** the assignment is refused and the profile is unchanged

#### Scenario: Unapproved tune
- **WHEN** an unapproved generated tune is assigned to the race profile
- **THEN** the assignment is refused and the profile is unchanged
