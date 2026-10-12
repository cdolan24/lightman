# Spec Delta

## Purpose

Records timestamped vehicle data (OBD-II readings and GPS position) during a driving session into the car's own database so it can be analyzed and reported on later.

## ADDED Requirements

### Requirement: Logging sessions
The system SHALL group recorded data into sessions. Starting a session SHALL create a session record for the car with its start time and the active tune (if any); stopping it SHALL record the end time.

#### Scenario: Start and stop a session
- **WHEN** a logging session is started for a car with an active tune and later stopped
- **THEN** the car's database contains one session with a start time, an end time, and the tune's id

#### Scenario: Session without a tune
- **WHEN** a session is started with no active tune
- **THEN** the session is recorded with no tune reference

### Requirement: Periodic OBD-II sampling
While a session is running, the system SHALL sample engine RPM, vehicle speed, throttle position, coolant temperature, intake air temperature, and fuel level at a configurable rate (default 1 Hz) and store each sample with its wall-clock time and elapsed time since session start.

#### Scenario: Samples are recorded at the configured rate
- **WHEN** a session runs for 5 seconds at 2 Hz
- **THEN** approximately 10 samples are stored, each with elapsed time and all six PID fields

### Requirement: Numeric storage of readings
Each stored reading SHALL be a plain number in the reader's native unit (rpm, km/h, percent, degrees Celsius); readings that are unavailable SHALL be stored as null.

#### Scenario: Unavailable PID
- **WHEN** the vehicle does not report fuel level
- **THEN** the sample stores fuel level as null and the other readings normally

### Requirement: Tolerate disconnected adapter
The system SHALL keep logging when the OBD-II adapter is disconnected or a query fails, storing null readings rather than stopping the session.

#### Scenario: Adapter not connected
- **WHEN** a session runs and no OBD-II adapter is connected
- **THEN** samples are still stored with null OBD readings and no error is raised

### Requirement: GPS position in samples
When a GPS source is configured, each sample SHALL include the latest valid fix's latitude, longitude, and GPS speed; when no valid fix is available these fields SHALL be null.

#### Scenario: GPS fix available
- **WHEN** a sample is taken while the GPS has a valid fix
- **THEN** the sample includes that fix's latitude, longitude, and speed

#### Scenario: No GPS fix
- **WHEN** a sample is taken before the GPS acquires a fix
- **THEN** the sample's position fields are null

### Requirement: NMEA GPS input
The system SHALL read position from a GPS receiver emitting NMEA 0183 RMC sentences, ignoring sentences that fail checksum validation or report an invalid fix.

#### Scenario: Corrupt sentence
- **WHEN** a sentence with a bad checksum is received
- **THEN** it is ignored and the previous valid fix is retained
