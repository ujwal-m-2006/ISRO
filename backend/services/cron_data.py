"""
Read API data from cron job snapshots first, fall back to live NOAA fetch.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.job_store import job_store
from services.noaa_live_service import noaa_live_service, FLARE_THRESHOLDS, CLASS_MEANINGS
from services.solar_wind_service import solar_wind_service
from services.cme_service import cme_service
from services.earth_impact_service import earth_impact_service
from services.satellite_roster import get_roster

SOURCE = "NOAA SWPC GOES-18 (cron-cached)"


def get_summary() -> Dict[str, Any]:
    cached = job_store.load("live_summary", max_age_seconds=300)
    if cached:
        return cached
    return noaa_live_service.build_live_summary()


def get_flux(hours: int = 6) -> Dict[str, Any]:
    cached = job_store.load(f"flux_{hours}h", max_age_seconds=180)
    if cached:
        summary = get_summary()
        return {
            "points": cached["points"],
            "hours": hours,
            "data_source": SOURCE,
            "last_update": summary.get("last_update", ""),
            "thresholds": FLARE_THRESHOLDS,
        }
    summary = get_summary()
    return {
        "points": noaa_live_service.build_flux_history(hours),
        "hours": hours,
        "data_source": summary["data_source"],
        "last_update": summary["last_update"],
        "thresholds": FLARE_THRESHOLDS,
    }


def get_flares() -> Dict[str, Any]:
    cached = job_store.load("recent_flares", max_age_seconds=900)
    summary = get_summary()
    flares = cached if cached else noaa_live_service.fetch_recent_flares()
    return {
        "flares": flares,
        "data_source": SOURCE if cached else summary["data_source"],
        "last_update": summary["last_update"],
    }


def get_regions() -> Dict[str, Any]:
    cached = job_store.load("active_regions", max_age_seconds=1200)
    summary = get_summary()
    if cached:
        return {
            "regions": cached["regions"],
            "data_source": SOURCE,
            "last_update": summary.get("last_update", ""),
            "glossary": cached.get("glossary", {}),
        }
    return {
        "regions": noaa_live_service.fetch_active_regions(),
        "data_source": summary["data_source"],
        "last_update": summary["last_update"],
        "glossary": {
            "location": "Heliographic position e.g. N17W38 = 17°N, 38°W from central meridian",
            "area": "Sunspot area in millionths of solar hemisphere",
            "spot_class": "Zurich sunspot classification",
            "mag_class": "Magnetic complexity: E/F/G = flare productive",
            "c_probability_pct": "NOAA 24h C-class+ probability",
            "m_probability_pct": "NOAA 24h M-class+ probability",
            "x_probability_pct": "NOAA 24h X-class probability",
            "intensity_score": "Composite intensity score",
        },
    }


def get_nowcast() -> Dict[str, Any]:
    cached = job_store.load("nowcast", max_age_seconds=600)
    if cached:
        return cached
    return noaa_live_service.build_nowcast()


def get_forecast() -> Dict[str, Any]:
    cached = job_store.load("forecast", max_age_seconds=600)
    if cached:
        return cached
    return noaa_live_service.build_forecast()


def get_alerts() -> Dict[str, Any]:
    cached = job_store.load("alerts", max_age_seconds=600)
    if cached:
        return cached
    return noaa_live_service.build_alerts()


def get_flare_alerts() -> Dict[str, Any]:
    cached = job_store.load("flare_alerts", max_age_seconds=300)
    if cached:
        return cached
    from services.flare_alert_service import build_flare_alerts
    return build_flare_alerts()


def get_cron_status() -> Dict[str, Any]:
    return job_store.get_status()


def get_solar_wind_summary() -> Dict[str, Any]:
    cached = job_store.load("solar_wind_summary", max_age_seconds=180)
    if cached:
        return cached
    return solar_wind_service.build_summary()


def get_solar_wind_history() -> Dict[str, Any]:
    cached = job_store.load("solar_wind_history", max_age_seconds=180)
    summary = get_solar_wind_summary()
    points = cached["points"] if cached else solar_wind_service.build_history()
    return {
        "points": points,
        "data_source": summary["data_source"],
        "last_update": summary.get("last_update"),
    }


def get_cme_summary() -> Dict[str, Any]:
    cached = job_store.load("cme_summary", max_age_seconds=1800)
    if cached:
        return cached
    return cme_service.build_summary()


def get_earth_impact() -> Dict[str, Any]:
    cached = job_store.load("earth_impact", max_age_seconds=600)
    if cached:
        return cached
    return earth_impact_service.build_summary()


def get_satellite_roster() -> Dict[str, Any]:
    history = job_store.load("pradan_history", max_age_seconds=None) or {}
    return get_roster(history.get("instruments"))


def get_pradan_status() -> Dict[str, Any]:
    cached = job_store.load("pradan_status", max_age_seconds=None)
    if cached:
        return cached
    return {"authenticated": False, "error": "No PRADAN check has run yet.", "files": {}}


def get_pradan_history() -> Dict[str, Any]:
    cached = job_store.load("pradan_history", max_age_seconds=None)
    if cached:
        return cached
    return {"authenticated": False, "error": "No history backfill has run yet.", "instruments": {}}


def get_ensemble_forecast() -> Dict[str, Any]:
    cached = job_store.load("ensemble_forecast", max_age_seconds=600)
    if cached:
        return cached
    from services.flare_ensemble_service import build_ensemble_forecast
    return build_ensemble_forecast()


def get_cme_indicators() -> Dict[str, Any]:
    cached = job_store.load("cme_indicators", max_age_seconds=600)
    if cached:
        return cached
    from services.noaa_alerts_service import noaa_alerts_service
    return noaa_alerts_service.build_cme_indicators()


def get_storm_watches() -> Dict[str, Any]:
    cached = job_store.load("storm_watches", max_age_seconds=600)
    if cached:
        return cached
    from services.noaa_alerts_service import noaa_alerts_service
    return noaa_alerts_service.build_storm_watches()
