# obd_reader.py

import obd

class OBDReader:
    def __init__(self):
        self.connection = obd.OBD()  # auto-connects to USB or Bluetooth OBD-II

    def get_basic_data(self):
        data = {}
        queries = [
            ('rpm', obd.commands.RPM),
            ('speed', obd.commands.SPEED),
            ('throttle_pos', obd.commands.THROTTLE_POS),
            ('coolant_temp', obd.commands.COOLANT_TEMP),
            ('intake_temp', obd.commands.INTAKE_TEMP),
            ('fuel_level', obd.commands.FUEL_LEVEL),
        ]
        for key, cmd in queries:
            response = self.connection.query(cmd)
            data[key] = response.value if response.is_successful() else None
        return data

if __name__ == "__main__":
    reader = OBDReader()
    print(reader.get_basic_data())
