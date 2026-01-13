# dashboard.py

from flask import Flask, jsonify
from data_acquisition.obd_reader import OBDReader

app = Flask(__name__)
obd_reader = OBDReader()

@app.route('/api/obd')
def get_obd_data():
    data = obd_reader.get_basic_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
