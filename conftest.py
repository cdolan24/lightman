# conftest.py

import pytest

from tune_management import car_database


@pytest.fixture(autouse=True)
def temp_db_root(tmp_path, monkeypatch):
    """Keep every test's car databases in a throwaway directory."""
    monkeypatch.setattr(car_database, 'DB_ROOT', tmp_path / 'car_databases')
    return car_database.DB_ROOT
