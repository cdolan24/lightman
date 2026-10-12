# dashboard.py

from flask import Flask, jsonify

from data_acquisition.obd_reader import OBDReader
from tune_management.tune_switcher import TuneSwitcher
from user_interface.api import api

app = Flask(__name__)
app.register_blueprint(api)

# OBDReader connects on first use, so importing the dashboard doesn't touch hardware.
obd_reader = OBDReader()

def engine_rpm():
    return obd_reader.get_basic_data()['rpm']

app.config['SWITCHER_FACTORY'] = lambda car_id: TuneSwitcher(car_id, engine_rpm=engine_rpm)

@app.route('/api/obd')
def get_obd_data():
    data = obd_reader.get_basic_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
