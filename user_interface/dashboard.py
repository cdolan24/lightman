# dashboard.py

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from data_acquisition.obd_reader import OBDReader
from tune_management.tune_switcher import TuneSwitcher
from user_interface.api import api

STATIC = Path(__file__).parent / 'static'

def create_app(switcher_factory=TuneSwitcher):
    """The dashboard page plus the tune API. switcher_factory(car_id) supplies each request's TuneSwitcher."""
    app = Flask(__name__)
    app.register_blueprint(api)
    app.config['SWITCHER_FACTORY'] = switcher_factory

    @app.route('/')
    def index():
        return send_from_directory(STATIC, 'dashboard.html')

    return app

# Standalone mode (python -m user_interface.dashboard): no logger running, so read the adapter directly.
# OBDReader connects on first use, so importing the dashboard doesn't touch hardware.
obd_reader = OBDReader()

def engine_rpm():
    return obd_reader.get_basic_data()['rpm']

app = create_app(lambda car_id: TuneSwitcher(car_id, engine_rpm=engine_rpm))

@app.route('/api/obd')
def get_obd_data():
    # Queries the adapter directly; don't use while the data logger is running (use /api/cars/<id>/live).
    data = obd_reader.get_basic_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
