"""
Three-model flare-probability ensemble, each model shown separately plus a
combined estimate — this is a transparent weighted blend of real statistical
signals, not a trained ML model, and is presented honestly as such:

  Model A — NOAA official active-region + SWPC outlook probabilities
            (authoritative human-issued forecast, weighted highest)
  Model B — Live GOES flux-trend extrapolation (does current flux/short-term
            trend suggest rising or falling activity right now)
  Model C — Historical event-frequency (how many C/M/X events each currently
            active region has *already* produced this rotation — regions
            with a track record of flaring are more likely to keep flaring)

No model here — or anywhere — can predict flares with certainty. This
produces a probability estimate with each contributing signal shown
separately, so the basis for the number is visible rather than a black box.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from services.noaa_live_service import noaa_live_service

# Ensemble weights — NOAA's own issued forecast is authoritative and weighted
# highest; trend and historical-frequency are supporting signals.
WEIGHT_NOAA = 0.5
WEIGHT_TREND = 0.3
WEIGHT_HISTORY = 0.2

HORIZONS = [
    ("1 hour", 1),
    ("6 hours", 6),
    ("12 hours", 12),
    ("24 hours", 24),
    ("48 hours", 48),
    ("72 hours", 72),
]


def _model_a_noaa(regions: List[Dict[str, Any]], global_prob: Dict[str, Any], hours_ahead: int) -> Dict[str, float]:
    """NOAA's own official region probabilities + multi-day outlook."""
    top = regions[:8]
    avg_c = sum(r["c_probability_pct"] for r in top) / max(len(top), 1)
    avg_m = sum(r["m_probability_pct"] for r in top) / max(len(top), 1)
    avg_x = sum(r["x_probability_pct"] for r in top) / max(len(top), 1)

    if hours_ahead >= 24:
        day = min(3, hours_ahead // 24)
        avg_c = global_prob.get(f"c_class_{day}_day", avg_c)
        avg_m = global_prob.get(f"m_class_{day}_day", avg_m)
        avg_x = global_prob.get(f"x_class_{day}_day", avg_x)

    return {"c": avg_c, "m": avg_m, "x": avg_x}


def _model_b_trend(trend_pct_30min: float, hours_ahead: int) -> Dict[str, float]:
    """Live flux-trend extrapolation — a rising trend now matters more for
    near-term horizons and fades out for multi-day horizons (a 30-min trend
    says little about 3 days from now)."""
    decay = max(0.0, 1 - hours_ahead / 72)
    boost = max(trend_pct_30min, 0) * 0.5 * decay
    return {"c": min(99, boost), "m": min(99, boost * 0.6), "x": min(99, boost * 0.3)}


def _model_c_history(regions: List[Dict[str, Any]]) -> Dict[str, float]:
    """Historical event-frequency: each region's already-observed C/M/X event
    count this rotation, as a share of all currently-active regions' events —
    a region that has already produced 3 M-flares is empirically more likely
    to produce another than one that has produced zero."""
    total_c = sum(r.get("c_events", 0) for r in regions) or 1
    total_m = sum(r.get("m_events", 0) for r in regions) or 1
    total_x = sum(r.get("x_events", 0) for r in regions) or 1
    if not regions:
        return {"c": 0.0, "m": 0.0, "x": 0.0}

    # Scale each region's share of historical events into a 0-100 probability-
    # like score, then average across active regions (more regions with a
    # flaring track record -> higher overall chance).
    c_score = sum(min(99, (r.get("c_events", 0) / total_c) * 100 * len(regions)) for r in regions) / len(regions)
    m_score = sum(min(99, (r.get("m_events", 0) / total_m) * 100 * len(regions)) for r in regions) / len(regions)
    x_score = sum(min(99, (r.get("x_events", 0) / total_x) * 100 * len(regions)) for r in regions) / len(regions)
    return {"c": c_score, "m": m_score, "x": x_score}


def build_ensemble_forecast() -> Dict[str, Any]:
    summary = noaa_live_service.build_live_summary()
    regions = noaa_live_service.fetch_active_regions()
    global_prob = summary.get("global_probabilities") or {}
    trend = summary["flux_trend_pct_30min"]

    predictions = []
    for i, (label, hours) in enumerate(HORIZONS):
        model_a = _model_a_noaa(regions, global_prob, hours)
        model_b = _model_b_trend(trend, hours)
        model_c = _model_c_history(regions)

        combined = {
            k: round(min(99, model_a[k] * WEIGHT_NOAA + model_b[k] * WEIGHT_TREND + model_c[k] * WEIGHT_HISTORY), 1)
            for k in ("c", "m", "x")
        }

        if combined["x"] >= 15:
            flare_class, prob = "X", combined["x"] / 100
        elif combined["m"] >= 25:
            flare_class, prob = "M", combined["m"] / 100
        else:
            flare_class, prob = "C", combined["c"] / 100

        expected = datetime.now(timezone.utc) + timedelta(hours=hours)

        predictions.append(
            {
                "id": i + 1,
                "time_horizon": label,
                "hours_ahead": hours,
                "expected_time": expected.isoformat(),
                "flare_class": flare_class,
                "probability": round(prob, 3),
                "combined": combined,
                "models": {
                    "noaa_official": {k: round(v, 1) for k, v in model_a.items()},
                    "flux_trend": {k: round(v, 1) for k, v in model_b.items()},
                    "historical_frequency": {k: round(v, 1) for k, v in model_c.items()},
                },
                "weights": {"noaa_official": WEIGHT_NOAA, "flux_trend": WEIGHT_TREND, "historical_frequency": WEIGHT_HISTORY},
            }
        )

    return {
        "predictions": predictions,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "data_source": summary["data_source"],
        "methodology": (
            "Weighted ensemble of 3 real statistical signals: NOAA's own official active-region + "
            "SWPC outlook probabilities (50%), live GOES flux-trend extrapolation (30%), and each "
            "active region's historical C/M/X event frequency this rotation (20%). This is a "
            "transparent statistical blend, not a trained machine-learning model — solar flare "
            "timing and magnitude cannot be predicted with certainty by any method."
        ),
    }
