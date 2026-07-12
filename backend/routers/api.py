from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
import pytz

from schemas import HealthCheckResponse, StatusResponse
from schemas.live import (
    LiveSummaryResponse,
    FluxHistoryResponse,
    FlaresResponse,
    ActiveRegionsResponse,
    ExtendedNowcastResponse,
    ExtendedForecastResponse,
    SolarWindSummaryResponse,
    SolarWindHistoryResponse,
    CMESummaryResponse,
    EarthImpactResponse,
    SatelliteRosterResponse,
    EnsembleForecastResponse,
)
from services.cron_data import (
    get_summary,
    get_flux,
    get_flares,
    get_regions,
    get_nowcast,
    get_forecast,
    get_alerts,
    get_cron_status,
    get_solar_wind_summary,
    get_solar_wind_history,
    get_cme_summary,
    get_earth_impact,
    get_satellite_roster,
    get_pradan_status,
    get_pradan_history,
    get_ensemble_forecast,
    get_cme_indicators,
    get_storm_watches,
    get_flare_alerts,
)
from services.noaa_live_service import FLARE_THRESHOLDS, CLASS_MEANINGS

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
def health_check():
    return {
        "status": "healthy",
        "message": "Solar Flare Prediction API — cron-fed NOAA data",
        "timestamp": datetime.now(pytz.UTC).isoformat(),
    }


@router.get("/status", response_model=StatusResponse)
def status_check():
    cron = get_cron_status()
    jobs = cron.get("jobs", {})
    summary = get_summary()
    last_flux = jobs.get("fetch_flux", {})
    return {
        "status": "operational",
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "services": {
            "noaa_swpc": "connected",
            "cron_scheduler": "active",
            "fetch_flux": "ok" if last_flux.get("success") else "pending",
            "last_flux_cron": last_flux.get("last_run", "never"),
            "last_noaa_update": summary.get("last_update", "unknown"),
            "snapshots": str(len(cron.get("snapshots", []))),
        },
    }


@router.get("/jobs/status")
def jobs_status():
    """Cron job run history and snapshot metadata."""
    return get_cron_status()


@router.get("/live/summary", response_model=LiveSummaryResponse)
def get_live_summary():
    return get_summary()


@router.get("/live/flux", response_model=FluxHistoryResponse)
def get_live_flux(hours: int = 6):
    return get_flux(hours)


@router.get("/live/flares", response_model=FlaresResponse)
def get_live_flares():
    return get_flares()


@router.get("/live/regions", response_model=ActiveRegionsResponse)
def get_active_regions():
    return get_regions()


@router.get("/nowcast", response_model=ExtendedNowcastResponse)
def get_nowcast_prediction():
    return get_nowcast()


@router.get("/forecast", response_model=ExtendedForecastResponse)
def get_forecast_predictions():
    return get_forecast()


@router.get("/alerts")
def get_alerts_route():
    return get_alerts()


@router.get("/latest")
def get_latest_data():
    summary = get_summary()
    flux = summary["current_flux"]
    return {
        "solexs": {
            "soft_xray_flux": flux["shortwave_0_05_0_4_nm_wm2"],
            "energy_band": "0.05–0.4 nm (GOES shortwave / SoLEXS analog)",
            "observation_time": summary["last_update"],
            "instrument_status": "online",
            "quality_flag": "good",
            "detector_health": "GOES-18 operational",
            "timestamp": summary["last_update"],
        },
        "hel1os": {
            "hard_xray_flux": flux["longwave_0_1_0_8_nm_wm2"],
            "energy_band": "0.1–0.8 nm (GOES longwave / HEL1OS analog)",
            "observation_time": summary["last_update"],
            "instrument_status": "online",
            "quality_flag": "good",
            "detector_health": "GOES-18 operational",
            "current_class": summary["current_class"],
            "timestamp": summary["last_update"],
        },
        "last_updated": summary["last_update"],
        "data_source": summary["data_source"],
        "class_meanings": CLASS_MEANINGS,
    }


@router.get("/glossary")
def get_glossary():
    return {
        "flare_classes": CLASS_MEANINGS,
        "flux_thresholds_wm2": FLARE_THRESHOLDS,
        "instruments": {
            "GOES_shortwave": "0.05–0.4 nm — soft X-rays from hot coronal plasma (~2–20 MK)",
            "GOES_longwave": "0.1–0.8 nm — primary band for NOAA flare classification",
            "SoLEXS": "Aditya-L1 Solar Low Energy X-ray Spectrometer (2–22 keV) — ISRO equivalent",
            "HEL1OS": "Aditya-L1 High Energy L1 Orbiting X-ray Spectrometer (10–150 keV) — ISRO equivalent",
        },
        "data_sources": [
            "NOAA Space Weather Prediction Center — https://www.swpc.noaa.gov/",
            "GOES X-ray flux — https://www.swpc.noaa.gov/products/goes-x-ray-flux",
            "Active regions — https://www.swpc.noaa.gov/products/solar-region-summary",
        ],
        "cron_schedules": {
            "fetch_flux": "every 1 minute",
            "fetch_summary": "every 1 minute",
            "fetch_nowcast": "every 5 minutes",
            "fetch_alerts": "every 5 minutes",
            "fetch_forecast": "every 5 minutes",
            "fetch_flares": "every 10 minutes",
            "fetch_regions": "every 15 minutes",
            "fetch_solar_wind": "every 1 minute",
            "fetch_earth_impact": "every 5 minutes",
            "fetch_cme": "every 15 minutes",
            "full_sync": "every hour at :00 UTC",
        },
    }


@router.get("/space-weather/solar-wind", response_model=SolarWindSummaryResponse)
def get_solar_wind():
    return get_solar_wind_summary()


@router.get("/space-weather/solar-wind/history", response_model=SolarWindHistoryResponse)
def get_solar_wind_history_route():
    return get_solar_wind_history()


@router.get("/space-weather/cme", response_model=CMESummaryResponse)
def get_cme():
    return get_cme_summary()


@router.get("/space-weather/earth-impact", response_model=EarthImpactResponse)
def get_earth_impact_route():
    return get_earth_impact()


@router.get("/satellites", response_model=SatelliteRosterResponse)
def get_satellites():
    return get_satellite_roster()


@router.get("/pradan/status")
def get_pradan_status_route():
    return get_pradan_status()


@router.post("/pradan/backfill/trigger")
def trigger_pradan_backfill(background_tasks: BackgroundTasks):
    """Runs the full-history backfill in-process (same JobStore instance as
    the cron scheduler) rather than as a separate script — running it as a
    standalone process alongside the live server caused a torn concurrent
    write to job_status.json before (both processes writing the same file
    with no cross-process lock)."""
    from jobs.data_jobs import job_backfill_pradan_history

    background_tasks.add_task(job_backfill_pradan_history)
    return {"status": "triggered", "message": "PRADAN backfill running in background — check /pradan/history shortly"}


@router.get("/predictions/accuracy")
def get_prediction_accuracy():
    """Real computed accuracy from stored predictions verified against actual
    NOAA outcomes — not an asserted number. See services/prediction_verification.py."""
    from services.prediction_verification import get_all_accuracy

    return get_all_accuracy()


@router.post("/predictions/verify/trigger")
def trigger_prediction_verification(background_tasks: BackgroundTasks):
    from services.prediction_verification import record_all, verify_all

    def run():
        record_all()
        verify_all()

    background_tasks.add_task(run)
    return {"status": "triggered", "message": "Recording + verifying predictions in background"}


@router.get("/pradan/history")
def get_pradan_history_route():
    return get_pradan_history()


@router.get("/forecast/ensemble", response_model=EnsembleForecastResponse)
def get_ensemble_forecast_route():
    return get_ensemble_forecast()


@router.get("/space-weather/cme-indicators")
def get_cme_indicators_route(days: int = 7):
    if days == 7:
        return get_cme_indicators()
    from services.noaa_alerts_service import noaa_alerts_service
    return noaa_alerts_service.build_cme_indicators(days=days)


@router.get("/space-weather/storm-watches")
def get_storm_watches_route():
    return get_storm_watches()


@router.get("/flare-alerts")
def get_flare_alerts_route():
    return get_flare_alerts()
