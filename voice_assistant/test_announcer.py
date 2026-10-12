# test_announcer.py

import threading
import time
import unittest

from voice_assistant.announcer import Announcer

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

class TestAnnouncer(unittest.TestCase):
    def setUp(self):
        self.spoken = []
        self.clock = FakeClock()
        self.announcer = Announcer(self.spoken.append, clock=self.clock, start=False)

    def test_warning_first(self):
        self.announcer.say("Lap 2")
        self.clock.now = 1
        self.announcer.say("Coolant 112 degrees", priority='warning')
        self.announcer.drain()
        self.assertEqual(self.spoken, ["Coolant 112 degrees", "Lap 2"])

    def test_fifo_within_priority(self):
        for text in ("one", "two", "three"):
            self.announcer.say(text)
        self.announcer.drain()
        self.assertEqual(self.spoken, ["one", "two", "three"])

    def test_stale_messages_dropped(self):
        self.announcer.say("old news")
        self.announcer.say("old warning", priority='warning')
        self.clock.now = 20
        self.announcer.say("fresh")
        self.announcer.drain()
        self.assertEqual(self.spoken, ["old warning", "fresh"])

    def test_duplicates_collapsed(self):
        self.announcer.say("Low fuel")
        self.announcer.say("Low fuel")
        self.announcer.drain()
        self.assertEqual(self.spoken, ["Low fuel"])

    def test_unknown_priority(self):
        with self.assertRaises(ValueError):
            self.announcer.say("x", priority='urgent')

    def test_speech_error_is_isolated(self):
        def speak(text):
            if text == "bad":
                raise RuntimeError("audio device gone")
            self.spoken.append(text)
        announcer = Announcer(speak, clock=self.clock, start=False)
        announcer.say("bad")
        announcer.say("good")
        with self.assertLogs('voice_assistant.announcer', level='ERROR'):
            announcer.drain()
        self.assertEqual(self.spoken, ["good"])

class TestAnnouncerThread(unittest.TestCase):
    def test_say_does_not_block(self):
        release, spoken = threading.Event(), []
        def slow_speak(text):
            release.wait(5)
            spoken.append(text)
        announcer = Announcer(slow_speak)
        try:
            started = time.monotonic()
            announcer.say("first")
            announcer.say("second")
            self.assertLess(time.monotonic() - started, 0.5)
            release.set()
            deadline = time.monotonic() + 5
            while len(spoken) < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(spoken, ["first", "second"])
        finally:
            release.set()
            announcer.stop()

if __name__ == "__main__":
    unittest.main()
