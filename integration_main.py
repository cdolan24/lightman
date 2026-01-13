# integration_main.py

from data_acquisition.obd_reader import OBDReader
from tune_management.tune_manager import TuneManager
from tune_management.manual_override import ManualOverride
from tune_management.compliance_checker import ComplianceChecker
from voice_assistant.voice_feedback import VoiceAssistant

CAR_ID = 1

def main():
    # Initialize modules
    obd_reader = OBDReader()
    tune_manager = TuneManager(CAR_ID)
    manual_override = ManualOverride()
    compliance_checker = ComplianceChecker()
    voice_assistant = VoiceAssistant()

    # Get OBD data
    obd_data = obd_reader.get_basic_data()
    print("OBD Data:", obd_data)

    # Save a new tune
    tune_manager.save_tune("Street Mode", b"street_tune_data")
    tunes = tune_manager.list_tunes()
    print("Tunes:", tunes)

    # Manual override
    manual_override.activate_override("Street Mode")
    print("Override Status:", manual_override.get_status())

    # Compliance check
    is_legal = compliance_checker.is_street_legal(b"street_tune_data")
    print("Street legal?", is_legal)
    if is_legal:
        voice_assistant.speak("Tune is street legal.")
    else:
        voice_assistant.speak("Tune is not street legal.")

if __name__ == "__main__":
    main()
