# integration_main.py

"""Hardware smoke test: read OBD-II, report the active tune, and speak a status line."""

from data_acquisition.obd_reader import OBDReader, connect
from tune_management.compliance_checker import ComplianceChecker
from tune_management.tune_manager import TuneManager
from tune_management.tune_switcher import TuneSwitcher
from voice_assistant.voice_feedback import VoiceAssistant

CAR_ID = 1

def main(obd_timeout=30.0):
    obd_reader = OBDReader(connect(timeout=obd_timeout))
    print("OBD connected:", obd_reader.is_connected)
    print("OBD Data:", obd_reader.get_basic_data())

    switcher = TuneSwitcher(CAR_ID)
    active = switcher.active()
    print("Active tune:", active)

    if active['tune_id'] is None:
        message = "No tune is active."
    else:
        tune = TuneManager(CAR_ID).get_tune(active['tune_id'])
        legal = ComplianceChecker().is_street_legal(tune['data'])
        legality = {True: "is street legal", False: "is not street legal",
                    None: "has not been checked for street legality"}[legal]
        message = f"Active tune {tune['name']} {legality}."
    print(message)
    VoiceAssistant().speak(message)

if __name__ == "__main__":
    main()
