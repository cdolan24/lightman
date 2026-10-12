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
The system SHALL allow renaming a tune and deleting a tune. Deleting a tune that is assigned to a profile or currently active SHALL be refused.

#### Scenario: Rename
- **WHEN** tune "Old" is renamed to "New"
- **THEN** the library lists "New" with the same data

#### Scenario: Delete an assigned tune
- **WHEN** a tune assigned to the race profile is deleted
- **THEN** the deletion is refused and the tune remains

### Requirement: Export and import tunes
The system SHALL export a tune to a single portable file containing its name, notes, and data, and SHALL import such a file into any car's library as a new tune.

#### Scenario: Share between cars
- **WHEN** a tune exported from car 1 is imported into car 2
- **THEN** car 2's library contains a tune with the same name, notes, and data

#### Scenario: Invalid file
- **WHEN** a file that is not a Lightman tune export is imported
- **THEN** the import is refused and nothing is added
