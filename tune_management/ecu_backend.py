# ecu_backend.py

"""How a tune switch reaches the ECU.

Each backend declares a method:
  software - only records the selection (current default; Lightman stays plug-and-play via OBD-II)
  live     - flips the ECU's map-switch input, e.g. from a GPIO pin (future)
  flash    - writes the full tune image; TuneSwitcher only allows it with the engine off (future)
"""

class ECUError(Exception):
    pass

class ECUBackend:
    method = None

    def apply(self, tune):
        """Apply a tune dict (id, name, data, ...). Raise ECUError on failure."""
        raise NotImplementedError

class SoftwareBackend(ECUBackend):
    method = 'software'

    def apply(self, tune):
        pass

BACKENDS = {
    'software': SoftwareBackend,
}
