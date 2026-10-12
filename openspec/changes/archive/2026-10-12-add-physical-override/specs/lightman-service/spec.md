# Spec Delta

## ADDED Requirements

### Requirement: Physical override in the service
When an override pin is configured, the service SHALL start the physical override control for the configured car and mode, using the same sampled engine speed as other switch entry points. With no pin configured (the default), no override SHALL be started.

#### Scenario: Override configured
- **WHEN** the configuration sets `[override] pin = 17` and `mode = "button"`
- **THEN** the service starts a button override on GPIO 17 for the configured car

#### Scenario: Default
- **WHEN** no override pin is configured
- **THEN** the service runs without a physical override
