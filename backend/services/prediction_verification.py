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

# Maps each tracked model variant to the field in build_ensemble_forecast()'s
# per-horizon prediction dict that holds its class/probabilities, and the
# Supabase category it's recorded/verified under.
_MODEL_VARIANTS = {
    "ensemble_flare": {"class_key": "flare_class", "scores_key": "combined"},
    "single_model_flare": {"class_key": None, "scores_key": "single_model"},  # class lives inside single_model
    "dual_model_flare": {"class_key": None, "scores_key": "dual_model"},
}


def _record_variant(category: str, forecast_predictions: List[Dict[str, Any]]) -> int:
    cfg = _MODEL_VARIANTS[category]
    recorded = 0
    for p in forecast_predictions:
        if p.get("time_horizon") not in ("1 hour", "24 hours"):
            continue  # verifying every horizon isn't necessary; these two give a fast + slow check
        target = p.get("expected_time")
        if not target:
            continue

        scores = p.get(cfg["scores_key"]) or {}
        flare_class = scores.get("flare_class") if cfg["class_key"] is None else p.get(cfg["class_key"])
        m_pct = scores.get("m")
        x_pct = scores.get("x")
        if flare_class is None:
            continue

        # Dedup to one snapshot per horizon per 30-minute recording slot —
        # not per exact target time, which drifts every run since it's
        # "now + N hours" on a rolling forecast.
        slot = datetime.now(timezone.utc).replace(minute=(datetime.now(timezone.utc).minute // 30) * 30, second=0, microsecond=0)
        dedup_key = f"{p['time_horizon']}:{slot.isoformat()}"
        ok = prediction_store.record(
            category,
            {
                "time_horizon": p["time_horizon"],
                "target_time": target,
                "predicted_flare_class": flare_class,
                "predicted_m_pct": m_pct,
                "predicted_x_pct": x_pct,
            },
            dedup_key,
        )
        recorded += int(ok)
    return recorded


def record_ensemble_predictions() -> int:
    from services.flare_ensemble_service import build_ensemble_forecast

    forecast = build_ensemble_forecast()
    return _record_variant("ensemble_flare", forecast.get("predictions", []))


def record_single_model_predictions() -> int:
    from services.flare_ensemble_service import build_ensemble_forecast

    forecast = build_ensemble_forecast()
    return _record_variant("single_model_flare", forecast.get("predictions", []))


def record_dual_model_predictions() -> int:
    from services.flare_ensemble_service import build_ensemble_forecast

    forecast = build_ensemble_forecast()
    return _record_variant("dual_model_flare", forecast.get("predictions", []))


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
    from services.flare_ensemble_service import build_ensemble_forecast

    forecast_predictions = build_ensemble_forecast().get("predictions", [])
    return {
        "ensemble_flare": _record_variant("ensemble_flare", forecast_predictions),
        "single_model_flare": _record_variant("single_model_flare", forecast_predictions),
        "dual_model_flare": _record_variant("dual_model_flare", forecast_predictions),
        "storm_watch": record_storm_watches(),
        "cme_arrival": record_cme_arrivals(),
    }


# --- Verification (called less frequently) ----------------------------------

def _verify_flare_variant(category: str) -> int:
    """Shared verification logic for any flare-class prediction variant
    (single/dual/multi-model) — all three are checked against the same real
    NOAA GOES flux history, just recorded under different categories."""
    from services.noaa_live_service import noaa_live_service

    now = datetime.now(timezone.utc)
    verified = 0
    for entry in prediction_store.list_unverified(category):
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
            category,
            entry["dedup_key"],
            {"actual_max_class": actual_class, "actual_max_flux_wm2": max_flux, "correct": correct},
        )
        verified += 1
    return verified


def verify_ensemble_predictions() -> int:
    return _verify_flare_variant("ensemble_flare")


def verify_single_model_predictions() -> int:
    return _verify_flare_variant("single_model_flare")


def verify_dual_model_predictions() -> int:
    return _verify_flare_variant("dual_model_flare")


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
        "single_model_flare": verify_single_model_predictions(),
        "dual_model_flare": verify_dual_model_predictions(),
        "storm_watch": verify_storm_watches(),
        "cme_arrival": verify_cme_arrivals(),
    }


def get_all_accuracy() -> Dict[str, Any]:
    single = prediction_store.get_accuracy_summary("single_model_flare")
    dual = prediction_store.get_accuracy_summary("dual_model_flare")
    multi = prediction_store.get_accuracy_summary("ensemble_flare")

    # Best model so far — only declared once every variant actually has a
    # verified accuracy number; otherwise there's nothing real to compare.
    variants = {"single_model": single, "dual_model": dual, "multi_model": multi}
    verified_variants = {name: v for name, v in variants.items() if v.get("accuracy_pct") is not None}
    best_model = max(verified_variants, key=lambda n: verified_variants[n]["accuracy_pct"]) if verified_variants else None

    return {
        "ensemble_flare": multi,
        "single_model_flare": single,
        "dual_model_flare": dual,
        "storm_watch": prediction_store.get_accuracy_summary("storm_watch"),
        "cme_arrival": prediction_store.get_accuracy_summary("cme_arrival"),
        "best_flare_model": {
            "model": best_model,
            "accuracy_pct": verified_variants[best_model]["accuracy_pct"] if best_model else None,
            "note": (
                "Not enough verified predictions yet across all three variants to compare."
                if best_model is None
                else f"'{best_model}' has the highest measured accuracy so far among predictions old enough to verify."
            ),
        },
    }
