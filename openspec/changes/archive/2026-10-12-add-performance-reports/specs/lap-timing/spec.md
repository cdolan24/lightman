# Spec Delta

## ADDED Requirements

### Requirement: Lap tune attribution
Each recorded lap SHALL store the car's active tune at the moment the lap completed, or none if no tune was active.

#### Scenario: Tune changed mid-session
- **WHEN** lap 1 completes on the street tune, the driver switches to race, and lap 2 completes
- **THEN** lap 1 records the street tune and lap 2 records the race tune

### Requirement: Session track identity
A session with lap timing SHALL record its start/finish line, so laps from different tracks can be told apart. A session without lap timing SHALL record no line.

#### Scenario: Line recorded
- **WHEN** a session starts with a start/finish line
- **THEN** the session stores that line's two endpoints
