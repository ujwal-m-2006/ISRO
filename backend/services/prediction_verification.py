"""
Records this app's own predictions with a timestamp, then — once the
predicted window has actually passed — checks them against real historical
data and computes genuine accuracy. This is the only honest way to answer
"how accurate are these predictions": measure it, don't assert it.

Verification data sources (both real NOAA products, not our own output):
  - Flare class: NOAA GOES X-ray flux history (same feed everything else uses)
  - Storm watch / CME arrival: NOAA's 3-hourly planetary Kp index, 7-day
    history (services.swpc.noaa.gov/products/noaa-planetary-k-index.json) —
    a genuine CME impact manifests as elevated Kp, so this is a defensible
    real-world check for "did something actually happen", even though it's
    coarser than a direct solar-wind-speed jump (NOAA doesn't publish a
    multi-day solar wind history product we could use for that instead).
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from services import prediction_store

logger = logging.getLogger(__name__)

KP_HISTORY_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
CACHE_TTL_SECONDS = 900

_cache: Dict[str, Any] = {"data": None, "time": 0.0}
_lock = threading.Lock()


def _fetch_kp_history() -> List[Dict[str, Any]]:
    with _lock:
        now = time.time()
        if _cache["data"] is not None and now - _cache["time"] < CACHE_TTL_SECONDS:
            return _cache["data"]
        try:
            resp = requests.get(KP_HISTORY_URL, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.warning("Kp history fetch failed: %s", exc)
            return _cache["data"] or []
        _cache["data"] = data
        _cache["time"] = now
        return data


def _max_kp_in_window(start: datetime, end: datetime) -> Optional[float]:
    history = _fetch_kp_history()
    values = []
    for row in history:
        try:
            t = datetime.fromisoformat(row["time_tag"]).replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            continue
        if start <= t <= end:
            values.append(row.get("Kp"))
    values = [v for v in values if v is not None]
    return max(values) if values else None


def _kp_to_g_scale(kp: float) -> int:
    if kp >= 9:
        return 5
    if kp >= 8:
        return 4
    if kp >= 7:
        return 3
    if kp >= 6:
        return 2
    if kp >= 5:
        return 1
    return 0


# --- Recording (called frequently — dedup prevents duplicate spam) ---------

def record_ensemble_predictions() -> int:
    from services.flare_ensemble_service import build_ensemble_forecast

    forecast = build_ensemble_forecast()
    recorded = 0
    for p in forecast.get("predictions", []):
        if p.get("time_horizon") not in ("1 hour", "24 hours"):
            continue  # verifying every horizon isn't necessary; these two give a fast + slow check
        target = p.get("expected_time")
        if not target:
            continue
        # Dedup to one snapshot per horizon per 30-minute recording slot —
        # not per exact target time, which drifts every run since it's
        # "now + N hours" on a rolling forecast.
        slot = datetime.now(timezone.utc).replace(minute=(datetime.now(timezone.utc).minute // 30) * 30, second=0, microsecond=0)
        dedup_key = f"{p['time_horizon']}:{slot.isoformat()}"
        ok = prediction_store.record(
            "ensemble_flare",
            {
                "time_horizon": p["time_horizon"],
                "target_time": target,
                "predicted_flare_class": p.get("flare_class"),
                "predicted_m_pct": p.get("combined", {}).get("m"),
                "predicted_x_pct": p.get("combined", {}).get("x"),
            },
            dedup_key,
        )
        recorded += int(ok)
    return recorded


def record_storm_watches() -> int:
    from services.noaa_alerts_service import noaa_alerts_service

    data = noaa_alerts_service.build_storm_watches()
    recorded = 0
    for watch in data.get("watches", []):
        for day in watch.get("daily_forecast", []):
            dedup_key = f"{watch['product_id']}:{watch['issued']}:{day['day']}"
            ok = prediction_store.record(
                "storm_watch",
                {
                    "product_id": watch["product_id"],
                    "issued": watch["issued"],
                    "forecast_day": day["day"],
                    "predicted_level": day["level"],
                },
                dedup_key,
            )
            recorded += int(ok)
    return recorded


def record_cme_arrivals() -> int:
    from services.noaa_alerts_service import noaa_alerts_service

    data = noaa_alerts_service.build_cme_indicators(days=10)
    recorded = 0
    for e in data.get("events", []):
        est = e.get("arrival_estimate")
        if not est or not est.get("estimable"):
            continue
        dedup_key = f"{e['product_id']}:{e['begin_time']}"
        ok = prediction_store.record(
            "cme_arrival",
            {
                "product_id": e["product_id"],
                "begin_time": e["begin_time"],
                "velocity_km_s": e.get("velocity_km_s"),
                "earliest_plausible": est["earliest_plausible"]["arrival_time"],
                "nominal_arrival": est["nominal"]["arrival_time"],
                "latest_plausible": est["latest_plausible"]["arrival_time"],
            },
            dedup_key,
        )
        recorded += int(ok)
    return recorded


def record_all() -> Dict[str, int]:
    return {
        "ensemble_flare": record_ensemble_predictions(),
        "storm_watch": record_storm_watches(),
        "cme_arrival": record_cme_arrivals(),
    }


# --- Verification (called less frequently) ----------------------------------

def verify_ensemble_predictions() -> int:
    from services.noaa_live_service import noaa_live_service

    now = datetime.now(timezone.utc)
    verified = 0
    for entry in prediction_store.list_unverified("ensemble_flare"):
        target = datetime.fromisoformat(entry["target_time"])
        if now < target + timedelta(minutes=15):
            continue  # target window hasn't fully elapsed yet

        # Real observed flux in a window centered on the target time.
        hours_span = 168 if (now - target).days >= 2 else 24
        series = noaa_live_service.fetch_xray_series(hours_span)
        window_start = datetime.fromisoformat(entry["recorded_at"]) if entry.get("recorded_at") else target - timedelta(hours=1)
        actual_points = [
            p for p in series
            if window_start <= datetime.fromisoformat(p["time_tag"].replace("Z", "+00:00")) <= target + timedelta(minutes=30)
        ]
        if not actual_points:
            continue  # NOAA's rolling window no longer covers this old prediction — can't verify, leave pending

        max_flux = max(p["longwave_flux"] for p in actual_points)
        actual_letter, actual_class = noaa_live_service.flux_to_class(max_flux)
        predicted_letter = (entry.get("predicted_flare_class") or "")[:1]
        correct = predicted_letter == actual_letter

        prediction_store.mark_verified(
            "ensemble_flare",
            entry["dedup_key"],
            {"actual_max_class": actual_class, "actual_max_flux_wm2": max_flux, "correct": correct},
        )
        verified += 1
    return verified


def verify_storm_watches() -> int:
    now = datetime.now(timezone.utc)
    verified = 0
    for entry in prediction_store.list_unverified("storm_watch"):
        from services.noaa_alerts_service import noaa_alerts_service

        day_dt = noaa_alerts_service.parse_day_label(entry["forecast_day"], now)
        if day_dt is None:
            continue
        day_end = day_dt + timedelta(days=1)
        if now < day_end + timedelta(hours=3):
            continue  # the forecasted day (plus a margin for the last 3h Kp reading) hasn't fully passed

        max_kp = _max_kp_in_window(day_dt, day_end)
        if max_kp is None:
            continue  # outside Kp history's retention window — can't verify

        actual_g = _kp_to_g_scale(max_kp)
        predicted_g_match = entry["predicted_level"].split()[0]  # "G2" or "None"
        predicted_g = 0 if predicted_g_match == "None" else int(predicted_g_match.lstrip("G"))
        correct = actual_g >= predicted_g if predicted_g > 0 else actual_g == 0

        prediction_store.mark_verified(
            "storm_watch",
            entry["dedup_key"],
            {"actual_max_kp": max_kp, "actual_g_scale": actual_g, "correct": correct},
        )
        verified += 1
    return verified


def verify_cme_arrivals() -> int:
    now = datetime.now(timezone.utc)
    verified = 0
    for entry in prediction_store.list_unverified("cme_arrival"):
        latest = datetime.fromisoformat(entry["latest_plausible"])
        if now < latest + timedelta(hours=12):
            continue  # give a 12h buffer past the latest plausible arrival before checking

        earliest = datetime.fromisoformat(entry["earliest_plausible"])
        max_kp = _max_kp_in_window(earliest, latest + timedelta(hours=12))
        if max_kp is None:
            continue

        # A genuine CME impact should elevate geomagnetic activity — Kp>=4
        # ("active" or higher) within the predicted window is the real-world
        # signature we check for, since NOAA doesn't publish a multi-day
        # solar-wind-speed history product we could check more directly.
        disturbance_detected = max_kp >= 4
        prediction_store.mark_verified(
            "cme_arrival",
            entry["dedup_key"],
            {"actual_max_kp_in_window": max_kp, "correct": disturbance_detected},
        )
        verified += 1
    return verified


def verify_all() -> Dict[str, int]:
    return {
        "ensemble_flare": verify_ensemble_predictions(),
        "storm_watch": verify_storm_watches(),
        "cme_arrival": verify_cme_arrivals(),
    }


def get_all_accuracy() -> Dict[str, Any]:
    return {
        "ensemble_flare": prediction_store.get_accuracy_summary("ensemble_flare"),
        "storm_watch": prediction_store.get_accuracy_summary("storm_watch"),
        "cme_arrival": prediction_store.get_accuracy_summary("cme_arrival"),
    }
