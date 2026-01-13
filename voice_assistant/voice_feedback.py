# voice_feedback.py

import pyttsx3

class VoiceAssistant:
    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

if __name__ == "__main__":
    va = VoiceAssistant()
    va.speak("Lightman is online and ready.")
