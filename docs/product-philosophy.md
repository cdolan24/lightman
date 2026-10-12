# Product Philosophy

Lightman is an artificial agent that exists on a Raspberry Pi 5 and is wired into a car with an OBD-II port connector. It is able to use text to speech in order to explain potential problems to the user. It is also able to switch between ECU tunes on the fly, and can generate new ones for later on.

## Principles

- **Drag-and-drop onto a Pi.** Plugging into the OBD-II port and copying the software on should be all it takes. There is no hardwiring into the ECU (see the ECU backend roadmap in the README). Advanced work such as tune authoring, voice data and model updates lives in a separate [companion app](companion-app.md).
- **Safety before capability.** A bad tune can destroy an engine. Generated or imported tunes need human approval, a protected stock tune is always available, and flashing only happens with the engine off. See [tune safety](open-issues/tune-safety.md).
- **Honest status.** Lightman reports exactly what it did (for example, a `software` switch that didn't touch the ECU) and never claims success from placeholder code.
