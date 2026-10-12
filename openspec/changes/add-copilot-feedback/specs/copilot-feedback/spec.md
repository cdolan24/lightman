# Spec Delta

## Purpose

Speaks timely, prioritized feedback to the driver about engine health, lap times, recommendations and tune changes, so information reaches them without looking at a screen.

## ADDED Requirements

### Requirement: Non-blocking speech
Requesting an announcement SHALL return immediately. Announcements SHALL be spoken one at a time in the background, and a failure of the speech engine SHALL NOT raise an error to the requester.

#### Scenario: Slow speech engine
- **WHEN** an announcement is requested while another is still being spoken
- **THEN** the request returns without waiting and the announcement is spoken afterwards

#### Scenario: Speech engine error
- **WHEN** the speech engine raises an error while speaking
- **THEN** the error is logged, the requester is unaffected, and later announcements are still spoken

### Requirement: Priority and staleness
Pending warnings SHALL be spoken before pending routine messages. A pending announcement older than its maximum age (default 15 s for routine, 30 s for warnings) SHALL be discarded instead of spoken. An announcement identical to one already pending SHALL NOT be queued again.

#### Scenario: Warning jumps the queue
- **WHEN** a routine message and then a warning are pending
- **THEN** the warning is spoken first

#### Scenario: Stale message
- **WHEN** a routine message has waited 20 s
- **THEN** it is discarded

### Requirement: Critical coolant alert
During a session, when coolant temperature reaches the critical limit (default 110 °C), the system SHALL announce a warning stating the temperature. It SHALL NOT repeat the alert until either the temperature has dropped at least 5 °C below the limit and risen again, or the repeat interval (default 60 s) has passed while it stays high.

#### Scenario: Overheat
- **WHEN** coolant reads 112 °C
- **THEN** a warning mentioning 112 degrees is announced

#### Scenario: Stays hot
- **WHEN** coolant stays at 112 °C for 30 s after the alert
- **THEN** no further coolant alert is announced

#### Scenario: Still hot after the repeat interval
- **WHEN** coolant stays above the limit for 61 s after the alert
- **THEN** the alert is announced again

### Requirement: Low fuel alert
When fuel level drops to or below the low-fuel limit (default 10 %), the system SHALL announce it once, and again only after fuel has risen above the limit (for example after refuelling) and dropped again.

#### Scenario: Low fuel
- **WHEN** fuel level reads 8 %
- **THEN** a low-fuel message is announced once

### Requirement: OBD data loss alert
When a session's recent samples (default the last 5) all have no engine speed after the session previously had engine data, the system SHALL announce that engine data was lost. When engine data returns, it SHALL announce that once.

#### Scenario: Adapter unplugged mid-session
- **WHEN** engine speed was available and the last 5 samples have none
- **THEN** a warning that engine data was lost is announced once

### Requirement: Lap announcements
When a lap is completed in the current session, the system SHALL announce the lap number and lap time in minutes and seconds to one decimal place, and SHALL say when it is the best lap of the session.

#### Scenario: Best lap
- **WHEN** lap 2 completes in 92.4 s and lap 1 took 95.0 s
- **THEN** "Lap 2, 1 minute 32.4 seconds, best lap" (or equivalent) is announced

### Requirement: Recommendation announcements
The system SHALL announce a recommendation's reason when it first appears, and SHALL NOT announce it again while it remains continuously present. Warning-severity recommendations SHALL be announced as warnings.

#### Scenario: Persisting recommendation
- **WHEN** the same overheating recommendation is present on three consecutive checks
- **THEN** it is announced only once

### Requirement: Switch announcements
The system SHALL announce the result of each new switch attempt not initiated by voice. A successful switch SHALL name the profile or tune and, for the `software` method, state that the ECU was not changed. A failed switch SHALL state the reason. Switches made before the monitor started SHALL NOT be announced.

#### Scenario: Dashboard switch
- **WHEN** the dashboard switches to the race profile with the software backend
- **THEN** the announcement names the race profile and says the ECU was not changed

#### Scenario: Voice switch
- **WHEN** a switch is initiated by voice
- **THEN** the feedback monitor does not announce it

### Requirement: Configurable limits
The critical coolant, low fuel, OBD loss sample count, and alert repeat interval SHALL be overridable; unspecified limits SHALL use the defaults.

#### Scenario: Lower critical coolant
- **WHEN** the critical coolant limit is 100 °C and coolant reads 102 °C
- **THEN** a coolant warning is announced
