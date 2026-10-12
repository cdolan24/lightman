# tune-library Specification

## Purpose
Keeps each car's collection of tunes (name plus binary tune image) so users can save custom tunes, manage them, and share them between cars or users.

## Requirements

### Requirement: Save and retrieve tunes
The system SHALL store a tune for a specific car with a name, binary tune data, optional notes, and a creation time, and SHALL return a tune's full contents by id.

#### Scenario: Save then fetch
- **WHEN** a tune named "Track Day" is saved for car 1
- **THEN** listing car 1's tunes includes "Track Day", and fetching it by id returns the same data

#### Scenario: Unknown tune
- **WHEN** a tune id that does not exist for the car is fetched
- **THEN** the system reports the tune as not found

### Requirement: Tunes are scoped to a car
Tunes saved for one car SHALL NOT be visible in another car's library.

#### Scenario: Separate cars
- **WHEN** a tune is saved for car 1
- **THEN** car 2's tune list does not include it

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

### Requirement: Export and import tunes
The system SHALL export a tune to a single portable file containing its name, notes, and data, and SHALL import such a file into any car's library as a new tune.

#### Scenario: Share between cars
- **WHEN** a tune exported from car 1 is imported into car 2
- **THEN** car 2's library contains a tune with the same name, notes, and data

#### Scenario: Invalid file
- **WHEN** a file that is not a Lightman tune export is imported
- **THEN** the import is refused and nothing is added

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
