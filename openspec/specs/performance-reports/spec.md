# performance-reports Specification

## Purpose
Summarizes recorded sessions (lap times, engine stats) and compares how tunes perform on the same track, so the driver can judge tune effectiveness after a session.

## Requirements

### Requirement: Session list
The system SHALL list a car's sessions, newest first, with start and end time, duration, starting tune, and number of laps.

#### Scenario: List
- **WHEN** a car has three sessions
- **THEN** all three are listed, newest first, each with its lap count

### Requirement: Session lap summary
A session report SHALL include every lap with its number, time, and tune, plus the best lap, the average lap time, and the standard deviation of lap times (consistency). With fewer than two laps, the standard deviation SHALL be absent.

#### Scenario: Three laps
- **WHEN** a session has laps of 95.0 s, 92.0 s, and 93.0 s
- **THEN** the report shows best lap 2 (92.0 s), average 93.33 s, and a standard deviation of about 1.53 s

#### Scenario: No laps
- **WHEN** a session has no laps
- **THEN** the report has an empty lap list and no best, average, or deviation

### Requirement: Session engine stats
A session report SHALL include the maximum rpm, maximum speed, maximum and average coolant temperature, maximum intake air temperature, and fuel used (first minus last non-null fuel reading), ignoring null readings. A statistic with no readings SHALL be absent.

#### Scenario: Stats
- **WHEN** samples show rpm up to 6800, coolant between 85 °C and 104 °C, and fuel falling from 60 % to 52 %
- **THEN** the report shows max rpm 6800, max coolant 104, and fuel used 8

#### Scenario: Missing readings
- **WHEN** no sample in the session has intake air temperature
- **THEN** max intake air is absent and the other stats are reported

### Requirement: Unknown session
Requesting a report for a session that does not exist SHALL be reported as not found.

#### Scenario: Bad id
- **WHEN** a report for session 999 is requested and it does not exist
- **THEN** the system reports it as not found

### Requirement: Tune comparison per track
The system SHALL compare tunes using only laps with a recorded tune, grouped by track (start/finish line). For each track and tune it SHALL report the best lap, average lap, and lap count. Laps without a recorded tune or track SHALL be excluded.

#### Scenario: Two tunes, one track
- **WHEN** on the same track the race tune has laps of 90 s and 92 s and the street tune has laps of 96 s
- **THEN** the comparison for that track lists race (best 90, average 91, 2 laps) and street (best 96, average 96, 1 lap)

#### Scenario: Different tracks
- **WHEN** the race tune has laps on two different start/finish lines
- **THEN** they are reported under separate tracks and never averaged together

### Requirement: Report interfaces
Session lists, session reports, and tune comparisons SHALL be available from a command-line tool and over HTTP. Over HTTP, an unknown session SHALL return a not-found status.

#### Scenario: HTTP report
- **WHEN** a client requests the report of an existing session
- **THEN** it receives the lap summary and engine stats

#### Scenario: CLI comparison
- **WHEN** the tool is run with the comparison option
- **THEN** it prints each track's tunes with best and average lap times
