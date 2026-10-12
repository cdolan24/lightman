# announcer.py

import logging
import threading
import time

log = logging.getLogger(__name__)

PRIORITIES = {'warning': 0, 'info': 1}        # lower is spoken first
MAX_AGE = {'warning': 30.0, 'info': 15.0}     # seconds a message may wait before it's no longer worth saying

class Announcer:
    """Non-blocking, prioritized speech queue in front of a text-to-speech function."""

    def __init__(self, speak, clock=time.monotonic, start=True):
        self._speak = speak
        self._clock = clock
        self._pending = []   # (priority, queued_at, text)
        self._cond = threading.Condition()
        self._stopped = False
        self._thread = None
        if start:
            self._thread = threading.Thread(target=self._worker, name='announcer', daemon=True)
            self._thread.start()

    def say(self, text, priority='info'):
        """Queue text to be spoken; returns immediately. Duplicate pending messages are dropped."""
        if priority not in PRIORITIES:
            raise ValueError(f"priority must be one of {tuple(PRIORITIES)}")
        with self._cond:
            if any(t == text for _, _, t in self._pending):
                return
            self._pending.append((priority, self._clock(), text))
            self._cond.notify()

    def _next(self):
        """Pop the oldest highest-priority message that isn't stale. Caller holds the lock."""
        now = self._clock()
        self._pending = [m for m in self._pending if now - m[1] <= MAX_AGE[m[0]]]
        if not self._pending:
            return None
        message = min(self._pending, key=lambda m: (PRIORITIES[m[0]], m[1]))
        self._pending.remove(message)
        return message

    def _say_now(self, text):
        try:
            self._speak(text)
        except Exception:
            log.exception("Speech failed for %r", text)

    def drain(self):
        """Speak everything pending, synchronously (for tests and shutdown)."""
        while True:
            with self._cond:
                message = self._next()
            if message is None:
                return
            self._say_now(message[2])

    def _worker(self):
        while True:
            with self._cond:
                while not self._stopped and not self._pending:
                    self._cond.wait()
                if self._stopped:
                    return
                message = self._next()
            if message is not None:
                self._say_now(message[2])

    def stop(self):
        with self._cond:
            self._stopped = True
            self._cond.notify()
        if self._thread:
            self._thread.join(timeout=5)
