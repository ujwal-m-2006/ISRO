"""
APScheduler cron configuration for NOAA data ingestion.

Cron schedules (UTC):
  fetch_flux      — every 1 minute
  fetch_summary   — every 1 minute
  fetch_nowcast   — every 5 minutes
  fetch_alerts    — every 5 minutes
  fetch_forecast  — every 5 minutes
  fetch_flares    — every 10 minutes
  fetch_regions   — every 15 minutes
  full_sync       — every hour at :00
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from jobs.data_jobs import (
    job_backfill_pradan_history,
    job_check_pradan,
    job_fetch_alerts,
    job_fetch_cme,
    job_fetch_cme_indicators,
    job_fetch_flare_alerts,
    job_fetch_storm_watches,
    job_fetch_earth_impact,
    job_fetch_ensemble_forecast,
    job_fetch_flares,
    job_fetch_flux,
    job_fetch_forecast,
    job_fetch_nowcast,
    job_fetch_regions,
    job_fetch_solar_wind,
    job_fetch_summary,
    job_full_sync,
    job_record_predictions,
    job_verify_predictions,
)

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")

    # High-frequency flux (NOAA updates every ~1 min)
    scheduler.add_job(job_fetch_flux, CronTrigger(minute="*"), id="fetch_flux", replace_existing=True)
    scheduler.add_job(job_fetch_summary, CronTrigger(minute="*"), id="fetch_summary", replace_existing=True)

    # Analysis jobs
    scheduler.add_job(job_fetch_nowcast, CronTrigger(minute="*/5"), id="fetch_nowcast", replace_existing=True)
    scheduler.add_job(job_fetch_alerts, CronTrigger(minute="*/5"), id="fetch_alerts", replace_existing=True)
    scheduler.add_job(job_fetch_flare_alerts, CronTrigger(minute="*/5"), id="fetch_flare_alerts", replace_existing=True)
    scheduler.add_job(job_fetch_forecast, CronTrigger(minute="*/5"), id="fetch_forecast", replace_existing=True)

    # Catalogue jobs
    scheduler.add_job(job_fetch_flares, CronTrigger(minute="*/10"), id="fetch_flares", replace_existing=True)
    scheduler.add_job(job_fetch_regions, CronTrigger(minute="*/15"), id="fetch_regions", replace_existing=True)

    # Space weather (solar wind updates ~minutely at NOAA; CME/impact scales update slower)
    scheduler.add_job(job_fetch_solar_wind, CronTrigger(minute="*"), id="fetch_solar_wind", replace_existing=True)
    scheduler.add_job(job_fetch_earth_impact, CronTrigger(minute="*/5"), id="fetch_earth_impact", replace_existing=True)
    scheduler.add_job(job_fetch_cme, CronTrigger(minute="*/15"), id="fetch_cme", replace_existing=True)
    scheduler.add_job(job_fetch_cme_indicators, CronTrigger(minute="*/5"), id="fetch_cme_indicators", replace_existing=True)
    scheduler.add_job(job_fetch_storm_watches, CronTrigger(minute="*/5"), id="fetch_storm_watches", replace_existing=True)
    scheduler.add_job(job_fetch_ensemble_forecast, CronTrigger(minute="*/5"), id="fetch_ensemble_forecast", replace_existing=True)

    # Full sync on the hour
    scheduler.add_job(job_full_sync, CronTrigger(minute="0"), id="full_sync", replace_existing=True)

    # PRADAN login check — low frequency, it's a real government auth server
    scheduler.add_job(job_check_pradan, CronTrigger(hour="*/6"), id="check_pradan", replace_existing=True)

    # Full-mission history backfill — once daily, deliberately NOT run on
    # startup (see job_backfill_pradan_history docstring)
    scheduler.add_job(job_backfill_pradan_history, CronTrigger(hour="3", minute="0"), id="backfill_pradan_history", replace_existing=True)

    # Prediction accuracy tracking — record snapshots every 30 min (matches
    # the dedup slot in prediction_verification.py), verify hourly (most
    # predictions need hours before their target window has passed anyway)
    scheduler.add_job(job_record_predictions, CronTrigger(minute="0,30"), id="record_predictions", replace_existing=True)
    scheduler.add_job(job_verify_predictions, CronTrigger(minute="15"), id="verify_predictions", replace_existing=True)

    return scheduler


def start_scheduler(run_immediately: bool = True) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("Cron scheduler started (UTC)")

    if run_immediately:
        # Run in a background thread, not inline — this executes inside
        # FastAPI's startup event, and uvicorn won't serve a single request
        # (not even /health) until that event returns. job_full_sync alone
        # chains ~13 external HTTP calls (NOAA, NASA DONKI) plus a PRADAN
        # Keycloak login; if any of those is slow from wherever this is
        # hosted, blocking here means the whole app never starts responding.
        def _initial_sync() -> None:
            logger.info("Running initial full sync (background)...")
            job_full_sync()
            job_check_pradan()

        threading.Thread(target=_initial_sync, daemon=True, name="initial-sync").start()

    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Cron scheduler stopped")
    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    return _scheduler
