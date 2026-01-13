# test_voice_feedback.py

import unittest
from voice_assistant.voice_feedback import VoiceAssistant

class TestVoiceAssistant(unittest.TestCase):
    def test_speak(self):
        va = VoiceAssistant()
        try:
            va.speak("Testing voice feedback.")
        except Exception as e:
            self.fail(f"VoiceAssistant.speak() raised an exception: {e}")

if __name__ == "__main__":
    unittest.main()
