"""
Cron job handlers — fetch NOAA live data and persist snapshots.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from services.job_store import job_store
from services.noaa_live_service import noaa_live_service
from services.solar_wind_service import solar_wind_service
from services.cme_service import cme_service
from services.earth_impact_service import earth_impact_service
from services.flare_ensemble_service import build_ensemble_forecast
from services.noaa_alerts_service import noaa_alerts_service
from services import prediction_verification

logger = logging.getLogger(__name__)


def job_backfill_pradan_history() -> None:
    """Full-mission historical catalogue backfill — heavier (~1-2 min across
    both instruments), so this runs far less often than the other jobs
    (daily) and is never part of the immediate-on-startup sync, to avoid
    hitting PRADAN's server on every backend restart during development."""

    def work() -> str:
        from services.pradan_scraper import PRADANScraper
        from services.pradan_history import fetch_full_history, summarize_history

        scraper = PRADANScraper()
        if not scraper.authenticated:
            job_store.save("pradan_history", {"authenticated": False, "error": scraper.auth_error, "instruments": {}})
            return f"not authenticated: {scraper.auth_error}"

        instruments = {}
        for name in ("solexs", "hel1os", "velc", "suit", "papa", "mag", "swis", "steps"):
            files = fetch_full_history(scraper.session, name)
            instruments[name] = {"files": files, "summary": summarize_history(files)}
            # Persist incrementally so a partial run (e.g. interrupted on a
            # very large instrument like SWIS/STEPS) still leaves completed
            # instruments' data usable rather than losing everything.
            job_store.save("pradan_history", {"authenticated": True, "error": None, "instruments": dict(instruments)})

        return ", ".join(f"{k}={v['summary']['count']}" for k, v in instruments.items())

    _run("backfill_pradan_history", work)


def job_check_pradan() -> None:
    """Low-frequency check: log into PRADAN and list what's available.
    Never raises — records success/failure so the UI can show real status
    instead of silently failing."""

    def work() -> str:
        from services.pradan_scraper import PRADANScraper

        scraper = PRADANScraper()
        if not scraper.authenticated:
            job_store.save("pradan_status", {"authenticated": False, "error": scraper.auth_error, "files": {}})
            return f"not authenticated: {scraper.auth_error}"

        solexs_files = scraper.get_latest_solexs_data()
        hel1os_files = scraper.get_latest_hel1os_data()
        job_store.save(
            "pradan_status",
            {
                "authenticated": True,
                "error": None,
                "files": {
                    "solexs_count": len(solexs_files),
                    "hel1os_count": len(hel1os_files),
                    "solexs_latest": solexs_files[:5],
                    "hel1os_latest": hel1os_files[:5],
                },
            },
        )
        return f"authenticated, {len(solexs_files)} SoLEXS + {len(hel1os_files)} HEL1OS files listed"

    _run("check_pradan", work)


def job_fetch_adityal1_features() -> None:
    """Downloads and parses the single most recent real SoLEXS light curve
    available, caching just the derived counts+trend feature (not the raw
    FITS data) for trained_model_service.py's live dual/multi-model
    predictions. Deliberately not run on every cron tick — a full day's
    FITS file is a few MB and takes real time to download+parse, too heavy
    to do on every prediction request, so this refreshes periodically
    instead and the cached feature carries its own "as_of" timestamp so
    staleness is visible rather than hidden."""

    def work() -> str:
        from services.fits_parser import extract_light_curve_from_zip
        from services.pradan_scraper import PRADANScraper

        scraper = PRADANScraper()
        if not scraper.authenticated:
            return f"not authenticated: {scraper.auth_error}"

        files = scraper.get_latest_solexs_data()
        if not files:
            return "no SoLEXS files listed"

        latest = files[0]
        resp = scraper.session.get(latest["url"], timeout=60)
        resp.raise_for_status()
        points = extract_light_curve_from_zip(resp.content)
        if len(points) < 10:
            return f"file {latest['filename']} had too few real points ({len(points)})"

        # Same feature definition as training: current level + ~30min trend
        # (6 points at 5-min resample, but here we use the raw ~1Hz tail).
        recent = points[-1800:]  # last ~30 min at 1Hz
        counts_now = sum(p["counts"] for p in points[-60:]) / len(points[-60:])
        counts_30min_ago = sum(p["counts"] for p in recent[:60]) / len(recent[:60])
        trend = (counts_now - counts_30min_ago) / counts_30min_ago if counts_30min_ago > 0 else 0.0

        job_store.save(
            "adityal1_live_features",
            {
                "adityal1_counts": round(counts_now, 2),
                "adityal1_trend": round(max(-5.0, min(5.0, trend)), 4),
                "as_of": points[-1]["timestamp"],
                "source_file": latest["filename"],
            },
        )
        return f"{latest['filename']}: counts={counts_now:.1f} trend={trend:.3f}"

    _run("fetch_adityal1_features", work)


def _run(job_name: str, fn: Callable[[], str]) -> None:
    start = time.perf_counter()
    try:
        detail = fn()
        ms = (time.perf_counter() - start) * 1000
        job_store.record_run(job_name, True, detail, ms)
        logger.info("[CRON] %s OK (%s) in %.0fms", job_name, detail, ms)
    except Exception as exc:
        ms = (time.perf_counter() - start) * 1000
        job_store.record_run(job_name, False, str(exc), ms)
        logger.error("[CRON] %s FAILED: %s", job_name, exc)


def job_fetch_flux() -> None:
    def work() -> str:
        for hours in (6, 24):
            points = noaa_live_service.build_flux_history(hours)
            job_store.save(f"flux_{hours}h", {"points": points, "hours": hours})
        return "flux 6h+24h"

    _run("fetch_flux", work)


def job_fetch_summary() -> None:
    def work() -> str:
        summary = noaa_live_service.build_live_summary()
        job_store.save("live_summary", summary)
        return f"class={summary.get('current_class')}"

    _run("fetch_summary", work)


def job_fetch_regions() -> None:
    def work() -> str:
        regions = noaa_live_service.fetch_active_regions()
        glossary = {
            "location": "Heliographic position e.g. N17W38",
            "mag_class": "Magnetic complexity — E/F/G = flare productive",
            "c_probability_pct": "NOAA 24h C-class+ probability",
            "m_probability_pct": "NOAA 24h M-class+ probability",
            "x_probability_pct": "NOAA 24h X-class probability",
        }
        job_store.save("active_regions", {"regions": regions, "glossary": glossary})
        return f"{len(regions)} regions"

    _run("fetch_regions", work)


def job_fetch_flares() -> None:
    def work() -> str:
        flares = noaa_live_service.fetch_recent_flares()
        job_store.save("recent_flares", flares)
        return f"{len(flares)} flares"

    _run("fetch_flares", work)


def job_fetch_nowcast() -> None:
    def work() -> str:
        data = noaa_live_service.build_nowcast()
        job_store.save("nowcast", data)
        return f"class={data.get('current_flare_class')}"

    _run("fetch_nowcast", work)


def job_fetch_forecast() -> None:
    def work() -> str:
        data = noaa_live_service.build_forecast()
        job_store.save("forecast", data)
        return f"{len(data.get('predictions', []))} horizons"

    _run("fetch_forecast", work)


def job_fetch_alerts() -> None:
    def work() -> str:
        data = noaa_live_service.build_alerts()
        job_store.save("alerts", data)
        return f"{data.get('total_active', 0)} active"

    _run("fetch_alerts", work)


def job_fetch_flare_alerts() -> None:
    def work() -> str:
        from services.flare_alert_service import build_flare_alerts

        data = build_flare_alerts()
        job_store.save("flare_alerts", data)
        return f"{len(data.get('alerts', []))} flare alerts"

    _run("fetch_flare_alerts", work)


def job_fetch_solar_wind() -> None:
    def work() -> str:
        summary = solar_wind_service.build_summary()
        job_store.save("solar_wind_summary", summary)
        history = solar_wind_service.build_history()
        job_store.save("solar_wind_history", {"points": history})
        return f"speed={summary.get('speed_km_s')}km/s kp={summary.get('kp_index')}"

    _run("fetch_solar_wind", work)


def job_fetch_cme() -> None:
    def work() -> str:
        data = cme_service.build_summary()
        job_store.save("cme_summary", data)
        return f"{data.get('total_cmes', 0)} CMEs, {data.get('earth_directed_count', 0)} earth-directed"

    _run("fetch_cme", work)


def job_fetch_cme_indicators() -> None:
    def work() -> str:
        data = noaa_alerts_service.build_cme_indicators()
        job_store.save("cme_indicators", data)
        return f"{data.get('count', 0)} radio-burst CME indicators"

    _run("fetch_cme_indicators", work)


def job_fetch_storm_watches() -> None:
    def work() -> str:
        data = noaa_alerts_service.build_storm_watches()
        job_store.save("storm_watches", data)
        return f"{data.get('count', 0)} storm watches"

    _run("fetch_storm_watches", work)


def job_fetch_ensemble_forecast() -> None:
    def work() -> str:
        data = build_ensemble_forecast()
        job_store.save("ensemble_forecast", data)
        return f"{len(data.get('predictions', []))} horizons"

    _run("fetch_ensemble_forecast", work)


def job_fetch_earth_impact() -> None:
    def work() -> str:
        data = earth_impact_service.build_summary()
        job_store.save("earth_impact", data)
        return data.get("overall_earth_effect", "")

    _run("fetch_earth_impact", work)


def job_record_predictions() -> None:
    def work() -> str:
        counts = prediction_verification.record_all()
        return f"recorded {counts}"

    _run("record_predictions", work)


def job_verify_predictions() -> None:
    def work() -> str:
        counts = prediction_verification.verify_all()
        return f"verified {counts}"

    _run("verify_predictions", work)


def job_full_sync() -> None:
    """Hourly full NOAA sync — runs all fetch jobs in sequence."""
    job_fetch_flux()
    job_fetch_summary()
    job_fetch_regions()
    job_fetch_flares()
    job_fetch_nowcast()
    job_fetch_forecast()
    job_fetch_alerts()
    job_fetch_flare_alerts()
    job_fetch_solar_wind()
    job_fetch_cme()
    job_fetch_cme_indicators()
    job_fetch_storm_watches()
    job_fetch_earth_impact()
    job_fetch_ensemble_forecast()
    job_record_predictions()
    job_verify_predictions()
    logger.info("[CRON] full_sync completed")
