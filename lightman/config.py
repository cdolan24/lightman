# config.py

"""Lightman service configuration: a TOML file validated against DEFAULTS. Every setting is optional."""

import copy
import tomllib
from pathlib import Path

DEFAULTS = {
    'car_id': 1,
    'db_root': 'car_databases',
    'obd': {
        'port': '',            # '' = auto-detect
        'timeout': 30.0,       # seconds to wait for the adapter before logging without engine data
    },
    'logging': {
        'rate': 1.0,           # samples per second
    },
    'gps': {
        'port': '',            # '' = no GPS (no position, no lap timing)
        'baud': 9600,
    },
    'lap_timing': {
        'line': [],            # [lat1, lon1, lat2, lon2] start/finish line; needs gps.port
        'min_lap_time': 10.0,
    },
    'dashboard': {
        'host': '0.0.0.0',
        'port': 5000,
    },
    'voice': {
        'enabled': True,
    },
}

# Extra checks beyond "same type as the default": dotted key -> (test, message).
_CHECKS = {
    'car_id': (lambda v: v >= 1, "must be 1 or more"),
    'obd.timeout': (lambda v: v > 0, "must be greater than 0"),
    'logging.rate': (lambda v: 0 < v <= 20, "must be between 0 and 20"),
    'gps.baud': (lambda v: v > 0, "must be greater than 0"),
    'lap_timing.line': (lambda v: v == [] or (len(v) == 4 and all(isinstance(x, (int, float)) for x in v)),
                        "must be [lat1, lon1, lat2, lon2]"),
    'lap_timing.min_lap_time': (lambda v: v >= 0, "must be 0 or more"),
    'dashboard.port': (lambda v: 0 <= v <= 65535, "must be a port number"),
}

class ConfigError(ValueError):
    pass

def _merge(defaults, values, prefix=''):
    merged = copy.deepcopy(defaults)
    for key, value in values.items():
        dotted = prefix + key
        if key not in defaults:
            raise ConfigError(f"Unknown setting '{dotted}'")
        default = defaults[key]
        if isinstance(default, dict):
            if not isinstance(value, dict):
                raise ConfigError(f"'{dotted}' must be a table")
            merged[key] = _merge(default, value, dotted + '.')
            continue
        # Accept ints where floats are expected (rate = 2), but never bools for numbers.
        if isinstance(default, float) and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if type(value) is not type(default):
            raise ConfigError(f"'{dotted}' must be {type(default).__name__}, got {type(value).__name__}")
        check = _CHECKS.get(dotted)
        if check and not check[0](value):
            raise ConfigError(f"'{dotted}' {check[1]}")
        merged[key] = value
    return merged

def load_config(path=None):
    """Load and validate a config file. A missing file means all defaults."""
    if path is None or not Path(path).exists():
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, 'rb') as f:
            values = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML: {e}") from e
    config = _merge(DEFAULTS, values)
    if config['lap_timing']['line'] and not config['gps']['port']:
        raise ConfigError("'lap_timing.line' needs 'gps.port'")
    return config

def flatten(d, prefix=''):
    """{'gps': {'port': ''}} -> {'gps.port': ''}"""
    out = {}
    for key, value in d.items():
        if isinstance(value, dict):
            out.update(flatten(value, prefix + key + '.'))
        else:
            out[prefix + key] = value
    return out
