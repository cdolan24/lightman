# __main__.py

"""python -m lightman [--config PATH]"""

import argparse
import logging
import os
import signal
import sys

from lightman.config import ConfigError, load_config
from lightman.service import LightmanService

def main(argv=None):
    parser = argparse.ArgumentParser(prog='lightman', description="Run the Lightman copilot.")
    parser.add_argument('--config', default=os.environ.get('LIGHTMAN_CONFIG', 'lightman.toml'),
                        help="TOML config file (default: $LIGHTMAN_CONFIG or ./lightman.toml; missing = defaults)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"lightman: config error in {args.config}: {e}", file=sys.stderr)
        return 2

    service = LightmanService(config)
    def request_stop(signum, frame):
        service.stop_event.set()
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    if hasattr(signal, 'SIGBREAK'):  # Ctrl+Break on Windows
        signal.signal(signal.SIGBREAK, request_stop)

    service.start()
    try:
        while not service.wait(timeout=1.0):
            pass  # short waits keep the main thread responsive to signals
    finally:
        service.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
