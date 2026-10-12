# Spec Delta

## ADDED Requirements

### Requirement: Tune origin
Every tune SHALL record its origin: `stock`, `human`, `imported`, or `generated`. Tunes saved without a stated origin SHALL be `human`. Tunes added by import SHALL always be `imported`, whatever the export file says.

#### Scenario: Default origin
- **WHEN** a tune is saved without an origin
- **THEN** its origin is `human`

#### Scenario: Imported origin
- **WHEN** a tune exported from another car is imported
- **THEN** its origin is `imported`

### Requirement: Tune approval
`human` and `stock` tunes SHALL be approved when saved. `imported` and `generated` tunes SHALL start unapproved. Approving a tune SHALL record who approved it, when, and an optional note.

#### Scenario: Generated tune starts unapproved
- **WHEN** a tune with origin `generated` is saved
- **THEN** it is listed as unapproved

#### Scenario: Approve
- **WHEN** a person named "Connor" approves an unapproved tune from the dashboard
- **THEN** the tune is approved, with approver "Connor" and the approval time

### Requirement: Only people approve tunes
Approval SHALL only be accepted from the `dashboard`, `app`, or `manual` sources, and SHALL require a non-empty approver name. Approval requests from `voice`, `auto`, or any other source SHALL be refused.

#### Scenario: Auto approval refused
- **WHEN** approval of a generated tune is requested with source `auto`
- **THEN** the request is refused and the tune remains unapproved

#### Scenario: Missing approver
- **WHEN** approval is requested with an empty approver name
- **THEN** the request is refused

### Requirement: Tune data is immutable
Once a tune is saved, its data SHALL NOT be changed. Different data SHALL be stored as a new tune, so an approval always applies to exactly the data that was reviewed.

#### Scenario: Rename keeps approval and data
- **WHEN** an approved tune is renamed
- **THEN** its data and approval are unchanged

### Requirement: Stock tune
Each car SHALL be able to store at most one stock tune, with origin `stock`. Storing a second stock tune SHALL be refused.

#### Scenario: Store stock tune
- **WHEN** a stock tune is stored for a car that has none
- **THEN** it is saved as approved with origin `stock`

#### Scenario: Second stock tune
- **WHEN** a stock tune is stored for a car that already has one
- **THEN** the request is refused and the existing stock tune is unchanged

## MODIFIED Requirements

### Requirement: Rename and delete tunes
The system SHALL allow renaming a tune and deleting a tune. Deleting a tune that is assigned to a profile, is currently active, or is the car's stock tune SHALL be refused.

#### Scenario: Rename
- **WHEN** tune "Old" is renamed to "New"
- **THEN** the library lists "New" with the same data

#### Scenario: Delete an assigned tune
- **WHEN** a tune assigned to the race profile is deleted
- **THEN** the deletion is refused and the tune remains

#### Scenario: Delete the stock tune
- **WHEN** the car's stock tune is deleted
- **THEN** the deletion is refused and the stock tune remains
