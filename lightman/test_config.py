# test_config.py

from pathlib import Path

import pytest

from lightman.config import DEFAULTS, ConfigError, flatten, load_config

EXAMPLE = Path(__file__).parent.parent / 'lightman.example.toml'

def write(tmp_path, text):
    path = tmp_path / 'lightman.toml'
    path.write_text(text)
    return path

def test_missing_file_is_defaults(tmp_path):
    assert load_config(tmp_path / 'nope.toml') == DEFAULTS
    assert load_config(None) == DEFAULTS

def test_full_file(tmp_path):
    config = load_config(write(tmp_path, '''
car_id = 2
[logging]
rate = 2
[gps]
port = "/dev/ttyACM0"
[lap_timing]
line = [40.0, -105.0, 40.0001, -105.0]
[voice]
enabled = false
'''))
    assert config['car_id'] == 2
    assert config['logging']['rate'] == 2.0 and isinstance(config['logging']['rate'], float)
    assert config['gps'] == {'port': '/dev/ttyACM0', 'baud': 9600}
    assert config['lap_timing']['line'] == [40.0, -105.0, 40.0001, -105.0]
    assert config['voice']['enabled'] is False
    assert config['dashboard'] == DEFAULTS['dashboard']

@pytest.mark.parametrize('text, key', [
    ('[gps]\nprot = "/dev/ttyACM0"', "gps.prot"),
    ('carid = 2', "carid"),
    ('[logging]\nrate = -1', "logging.rate"),
    ('[logging]\nrate = "fast"', "logging.rate"),
    ('[voice]\nenabled = 1', "voice.enabled"),
    ('car_id = true', "car_id"),
    ('gps = 5', "gps"),
    ('[lap_timing]\nline = [1, 2, 3]', "lap_timing.line"),
    ('[gps]\nport = ""\n[lap_timing]\nline = [1, 2, 3, 4]', "lap_timing.line"),
    ('[dashboard]\nport = 70000', "dashboard.port"),
])
def test_errors_name_the_setting(tmp_path, text, key):
    with pytest.raises(ConfigError, match=f"'{key}'"):
        load_config(write(tmp_path, text))

def test_invalid_toml(tmp_path):
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(write(tmp_path, 'car_id = '))

def test_example_file_is_the_defaults():
    assert load_config(EXAMPLE) == DEFAULTS
    text = EXAMPLE.read_text()
    for dotted in flatten(DEFAULTS):
        assert dotted.split('.')[-1] in text
