# Spec Delta

## Purpose

Shows the driver and crew what the car is doing right now (live readings, laps, tune status and alerts) and offers the quick tune actions, on any device on the Pi's network.

## ADDED Requirements

### Requirement: Live session data
The system SHALL provide the car's in-progress logging session, its latest sample with the sample's age in seconds, and the session's completed laps with the best lap identified. When no session is in progress, the session and sample SHALL be reported as absent.

#### Scenario: Session running
- **WHEN** a session is in progress with samples and two laps of 95.0 s and 92.4 s
- **THEN** the response contains the session, the latest sample with its age, both laps, and lap 2 as the best lap

#### Scenario: No session
- **WHEN** no session is in progress
- **THEN** the response reports no session, no sample, and no laps

### Requirement: Single reader of the OBD adapter
The live session data SHALL be served from recorded samples and SHALL NOT query the OBD-II adapter.

#### Scenario: Logger owns the adapter
- **WHEN** live data is requested
- **THEN** no OBD-II query is made

### Requirement: Dashboard page
The system SHALL serve a dashboard page at the root path that displays live readings, lap timing, the active tune and profile with the switch method, current recommendations, and recent switch results for a car selected by a `car` query parameter (default 1).

#### Scenario: Open dashboard
- **WHEN** a browser requests `/?car=2`
- **THEN** an HTML page is returned that loads car 2's data from the API

### Requirement: Works offline
The dashboard page SHALL NOT load any resource from outside the Pi.

#### Scenario: No internet in the car
- **WHEN** the dashboard is opened on a network without internet access
- **THEN** the page and all its scripts and styles load from the Pi

### Requirement: Dashboard actions
The dashboard SHALL offer switching to each profile and reverting to stock, sent with source `dashboard`. It SHALL show the result, including refusal reasons. It SHALL NOT offer tune approval.

#### Scenario: Switch from dashboard
- **WHEN** the race button is pressed
- **THEN** a switch to the race profile with source `dashboard` is requested and its result is shown

### Requirement: Stale data indication
The dashboard SHALL indicate when no session is running, and when the latest sample is older than 5 s.

#### Scenario: Logger stopped responding
- **WHEN** the latest sample is 12 s old
- **THEN** the dashboard marks the live readings as stale
