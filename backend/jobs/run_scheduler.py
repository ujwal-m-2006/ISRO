#!/usr/bin/env python3
"""
Standalone cron scheduler process.
Run: python -m jobs.run_scheduler
"""

import logging
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from jobs.scheduler import start_scheduler, stop_scheduler


def main() -> None:
    start_scheduler(run_immediately=True)

    def shutdown(signum, frame):
        stop_scheduler()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logging.getLogger(__name__).info("Cron scheduler running — Ctrl+C to stop")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
