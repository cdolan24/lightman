# service.py

"""Runs the data logger, spoken feedback and dashboard together for one car."""

import logging
import threading
from pathlib import Path

from werkzeug.serving import make_server

from data_acquisition import obd_reader
from data_acquisition.data_logger import DataLogger, close_stale_sessions, sampled_engine_rpm
from data_acquisition.gps_reader import open_serial_gps
from tune_management import car_database
from tune_management.override_control import OverrideControl, attach_gpio
from tune_management.tune_switcher import TuneSwitcher
from user_interface.dashboard import create_app
from voice_assistant.announcer import Announcer
from voice_assistant.feedback_monitor import FeedbackMonitor

log = logging.getLogger('lightman')

def default_make_speak():
    from voice_assistant.voice_feedback import VoiceAssistant
    return VoiceAssistant().speak

def supervise(name, target, stop_event, restart_delay=5.0):
    """Run target until stop_event is set; if it crashes or returns early, log it and restart after a delay."""
    while not stop_event.is_set():
        try:
            target()
        except Exception:
            log.exception("%s crashed; restarting in %.0f s", name, restart_delay)
        else:
            if stop_event.is_set():
                return
            log.warning("%s stopped unexpectedly; restarting in %.0f s", name, restart_delay)
        stop_event.wait(restart_delay)

class LightmanService:
    def __init__(self, config, obd_connect=obd_reader.connect, open_gps=open_serial_gps,
                 make_speak=default_make_speak, restart_delay=5.0, feedback_interval=1.0, gpio_pin_factory=None):
        self.config = config
        self.car_id = config['car_id']
        self._obd_connect = obd_connect
        self._open_gps = open_gps
        self._make_speak = make_speak
        self._restart_delay = restart_delay
        self._feedback_interval = feedback_interval
        self._gpio_pin_factory = gpio_pin_factory
        self.stop_event = threading.Event()
        self._threads = []
        self.server = None
        self.announcer = None
        self.override_device = None

    @property
    def port(self):
        return self.server.server_port

    def start(self):
        car_database.DB_ROOT = Path(self.config['db_root'])
        closed = close_stale_sessions(self.car_id)
        if closed:
            log.info("Closed %d session(s) left open by a power loss", closed)

        # Dashboard first, so it's reachable while the OBD adapter is still connecting.
        car_id = self.car_id
        app = create_app(self._switcher)
        dash = self.config['dashboard']
        self.server = make_server(dash['host'], dash['port'], app, threaded=True)
        log.info("Dashboard on http://%s:%d/?car=%d", dash['host'], self.port, car_id)
        self._spawn('dashboard', self.server.serve_forever, supervised=False)

        self._spawn('logger', self._run_logger)

        if self.config['voice']['enabled']:
            try:
                self.announcer = Announcer(self._make_speak())
            except Exception:
                log.exception("Text-to-speech unavailable; voice feedback disabled")
        else:
            log.info("Voice feedback disabled in config")
        if self.announcer:
            self.announcer.say("Lightman copilot online.")
            self._spawn('feedback', lambda: FeedbackMonitor(car_id, self.announcer).run(
                self._feedback_interval, self.stop_event))

        self._start_override()

    @staticmethod
    def _switcher(car_id):
        # Engine speed for safety checks comes from recorded samples; the logger owns the adapter.
        return TuneSwitcher(car_id, engine_rpm=lambda: sampled_engine_rpm(car_id))

    def _start_override(self):
        cfg = self.config['override']
        if cfg['pin'] < 0:
            return
        try:
            self.override_device = attach_gpio(OverrideControl(self._switcher(self.car_id)), cfg['pin'],
                                               cfg['mode'], cfg['long_press'], pin_factory=self._gpio_pin_factory)
            log.info("Physical override (%s) on GPIO %d", cfg['mode'], cfg['pin'])
        except Exception:
            log.exception("Physical override on GPIO %d unavailable; override disabled", cfg['pin'])

    def _run_logger(self):
        obd_cfg, gps_cfg = self.config['obd'], self.config['gps']
        reader = obd_reader.OBDReader(self._obd_connect(obd_cfg['port'] or None, obd_cfg['timeout']))
        if reader.is_connected:
            log.info("OBD-II adapter connected")
        else:
            log.warning("OBD-II adapter not reachable; logging without engine data")

        gps, line = None, None
        if gps_cfg['port']:
            try:
                gps = self._open_gps(gps_cfg['port'], gps_cfg['baud'])
                log.info("GPS on %s", gps_cfg['port'])
            except Exception:
                log.exception("GPS on %s unavailable; logging without position or lap timing", gps_cfg['port'])
        lap_cfg = self.config['lap_timing']
        if gps and lap_cfg['line']:
            lat1, lon1, lat2, lon2 = lap_cfg['line']
            line = ((lat1, lon1), (lat2, lon2))

        logger = DataLogger(self.car_id, reader, gps=gps, lap_line=line,
                            min_lap_time=lap_cfg['min_lap_time'], rate_hz=self.config['logging']['rate'])
        logger.run(stop_event=self.stop_event)

    def _spawn(self, name, target, supervised=True):
        body = (lambda: supervise(name, target, self.stop_event, self._restart_delay)) if supervised else target
        thread = threading.Thread(target=body, name=name, daemon=True)
        thread.start()
        self._threads.append(thread)

    def wait(self, timeout=None):
        """Block until stop is requested (e.g. by a signal handler setting stop_event)."""
        return self.stop_event.wait(timeout)

    def stop(self):
        self.stop_event.set()
        if self.server:
            self.server.shutdown()
        for thread in self._threads:
            thread.join(timeout=10)
        if self.announcer:
            self.announcer.stop()
        if self.override_device:
            self.override_device.close()
        log.info("Lightman stopped")
