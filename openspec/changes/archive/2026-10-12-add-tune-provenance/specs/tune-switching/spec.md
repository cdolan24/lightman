# Spec Delta

## ADDED Requirements

### Requirement: Only approved tunes are activated
A switch to an unapproved tune SHALL be refused, whatever its source, and the refusal SHALL be recorded in the switch history.

#### Scenario: Unapproved tune by id
- **WHEN** the app requests a switch to an unapproved imported tune
- **THEN** the switch is refused with a reason stating the tune is not approved, and the active tune is unchanged

### Requirement: Automatic switching is limited to profiles
Switch requests with source `auto` SHALL only name a profile. A request from `auto` that names a tune id SHALL be refused and recorded.

#### Scenario: Auto by profile
- **WHEN** `auto` requests a switch to the street profile, which has an approved tune
- **THEN** the switch succeeds

#### Scenario: Auto by tune id
- **WHEN** `auto` requests a switch to a specific tune id
- **THEN** the switch is refused and the active tune is unchanged

### Requirement: Revert to stock
The system SHALL provide a revert-to-stock switch that activates the car's stock tune. It SHALL be available from every source and SHALL go through the same backend and engine-off rules as any other switch. If the car has no stock tune, the revert SHALL be refused.

#### Scenario: Revert
- **WHEN** the race tune is active and a revert to stock is requested by voice
- **THEN** the stock tune becomes active, the active profile is cleared, and the history records the revert

#### Scenario: No stock tune
- **WHEN** a revert to stock is requested for a car with no stock tune
- **THEN** the revert is refused with a reason stating there is no stock tune

#### Scenario: Revert needing a flash while running
- **WHEN** a revert to stock is requested on a flash backend while the engine reads 3000 rpm
- **THEN** the revert is refused because the engine must be off

### Requirement: HTTP approval and revert
The HTTP interface SHALL report each tune's origin and approval status, SHALL accept tune approval requests (subject to the approval source rules), and SHALL accept revert-to-stock requests.

#### Scenario: Approve over HTTP
- **WHEN** a client posts an approval for an imported tune with source `dashboard` and approver "Connor"
- **THEN** the response reports the tune as approved

#### Scenario: Auto approval over HTTP
- **WHEN** a client posts an approval with source `auto`
- **THEN** the response has an error status and the tune remains unapproved
