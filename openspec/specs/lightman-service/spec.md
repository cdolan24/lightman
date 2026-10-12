# lightman-service Specification

## Purpose
Runs all of Lightman's on-car functions (logging, spoken feedback, dashboard and API) as one service that starts at boot from a single configuration, so the Pi works as a drag-and-drop install.

## Requirements

### Requirement: Single service
The system SHALL provide one command that runs the data logger, the feedback monitor, and the dashboard/API server together for one configured car.

#### Scenario: Start the service
- **WHEN** the service is started with a configuration for car 1
- **THEN** a logging session for car 1 begins, feedback monitoring runs, and the dashboard is served on the configured port

### Requirement: Configuration file
The system SHALL read settings from a TOML file given by a command-line option or the `LIGHTMAN_CONFIG` environment variable, defaulting to `lightman.toml` in the working directory. Every setting SHALL have a default, so the service starts without any file. Unknown settings or invalid values SHALL stop startup with an error naming the setting.

#### Scenario: No config file
- **WHEN** the service starts and no configuration file exists
- **THEN** it runs with defaults (car 1, 1 Hz logging, dashboard on port 5000, voice enabled, no GPS)

#### Scenario: Typo in config
- **WHEN** the configuration contains `[gps] prot = "/dev/ttyACM0"`
- **THEN** startup fails with an error naming `gps.prot` as unknown

#### Scenario: Bad value
- **WHEN** the configuration sets `[logging] rate = -1`
- **THEN** startup fails with an error naming `logging.rate`

### Requirement: Degrade instead of fail
A missing or failing OBD-II adapter, GPS receiver, or audio output SHALL disable only the affected feature, with a logged message, while the rest of the service keeps running. An unexpected error inside one component SHALL be logged and SHALL NOT stop the other components.

#### Scenario: No audio device
- **WHEN** text-to-speech cannot be initialised
- **THEN** the service runs without spoken feedback and logs that voice is disabled

#### Scenario: GPS port missing
- **WHEN** the configured GPS port cannot be opened
- **THEN** logging continues without position or lap timing, and the problem is logged

### Requirement: Engine speed from recorded samples
Within the service, the engine speed used by tune switching safety checks SHALL come from the latest recorded sample of the open session if it is at most 2 s old. Otherwise engine speed SHALL be treated as unknown. The service SHALL NOT query the OBD-II adapter for this.

#### Scenario: Fresh sample
- **WHEN** the latest sample is 1 s old with 0 rpm
- **THEN** the switching engine-speed check reads 0 rpm

#### Scenario: Stale sample
- **WHEN** the latest sample is 10 s old
- **THEN** the switching engine-speed check reads unknown

### Requirement: Clean shutdown
On a termination signal or interrupt, the service SHALL stop sampling, record the session's end time, stop speech, and stop the server.

#### Scenario: systemd stop
- **WHEN** the service receives SIGTERM during a session
- **THEN** the session has an end time and the process exits

### Requirement: Start at boot on a Pi
The project SHALL include a systemd unit and an install script that sets up the Python environment and enables the service to start at boot and restart after a crash.

#### Scenario: Install
- **WHEN** the install script is run on a Raspberry Pi from the repository directory
- **THEN** the Python environment is created, the service is enabled, and it starts at the next boot

### Requirement: Physical override in the service
When an override pin is configured, the service SHALL start the physical override control for the configured car and mode, using the same sampled engine speed as other switch entry points. With no pin configured (the default), no override SHALL be started.

#### Scenario: Override configured
- **WHEN** the configuration sets `[override] pin = 17` and `mode = "button"`
- **THEN** the service starts a button override on GPIO 17 for the configured car

#### Scenario: Default
- **WHEN** no override pin is configured
- **THEN** the service runs without a physical override
