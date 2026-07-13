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

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from services.noaa_live_service import noaa_live_service

logger = logging.getLogger(__name__)

# Default ensemble weights — NOAA's own issued forecast is authoritative and
# weighted highest; trend and historical-frequency are supporting signals.
# These are the starting point only: _adaptive_weights() below shifts them
# based on which combination (single/dual/multi model) has actually been
# measured most accurate against real outcomes so far.
WEIGHT_NOAA = 0.5
WEIGHT_TREND = 0.3
WEIGHT_HISTORY = 0.2


def _adaptive_weights() -> Tuple[float, float, float]:
    """Adjusts the multi-model blend toward whichever variant (single model
    alone / dual model / full multi-model) has the best real, verified
    accuracy so far — not a static guess. Falls back to the default weights
    above until there's enough verified prediction history to judge from
    (accuracy_pct is None until at least one prediction has been checked
    against a real outcome), so this never claims false confidence early on.
    """
    try:
        from services import prediction_store

        single_acc = prediction_store.get_accuracy_summary("single_model_flare").get("accuracy_pct")
        dual_acc = prediction_store.get_accuracy_summary("dual_model_flare").get("accuracy_pct")
        multi_acc = prediction_store.get_accuracy_summary("ensemble_flare").get("accuracy_pct")
    except Exception as exc:
        logger.warning("Adaptive weight lookup failed, using defaults: %s", exc)
        return WEIGHT_NOAA, WEIGHT_TREND, WEIGHT_HISTORY

    if single_acc is None or dual_acc is None or multi_acc is None:
        return WEIGHT_NOAA, WEIGHT_TREND, WEIGHT_HISTORY

    accuracies = {"single": single_acc, "dual": dual_acc, "multi": multi_acc}
    best = max(accuracies, key=lambda k: accuracies[k])

    if best == "single":
        # NOAA's own forecast alone has out-predicted the blends — lean on it
        return 0.8, 0.15, 0.05
    if best == "dual":
        # Adding the historical-frequency signal hasn't helped — drop its weight
        return 0.55, 0.35, 0.10
    # Multi-model blend is already winning — keep the default 3-way split
    return WEIGHT_NOAA, WEIGHT_TREND, WEIGHT_HISTORY

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


def _class_from(scores: Dict[str, float]) -> Tuple[str, float]:
    if scores["x"] >= 15:
        return "X", scores["x"] / 100
    if scores["m"] >= 25:
        return "M", scores["m"] / 100
    return "C", scores["c"] / 100


def build_ensemble_forecast() -> Dict[str, Any]:
    summary = noaa_live_service.build_live_summary()
    regions = noaa_live_service.fetch_active_regions()
    global_prob = summary.get("global_probabilities") or {}
    trend = summary["flux_trend_pct_30min"]
    w_noaa, w_trend, w_history = _adaptive_weights()

    predictions = []
    for i, (label, hours) in enumerate(HORIZONS):
        model_a = _model_a_noaa(regions, global_prob, hours)
        model_b = _model_b_trend(trend, hours)
        model_c = _model_c_history(regions)

        # Three tracked variants, each recorded and verified separately so
        # their real accuracy can be compared honestly rather than assumed:
        #   single = NOAA's own official forecast alone (1 model)
        #   dual   = NOAA + live flux-trend, equally weighted (2 models)
        #   multi  = all 3 signals, blended with the adaptive weights above
        single = {k: round(model_a[k], 1) for k in ("c", "m", "x")}
        dual = {k: round((model_a[k] + model_b[k]) / 2, 1) for k in ("c", "m", "x")}
        multi = {
            k: round(min(99, model_a[k] * w_noaa + model_b[k] * w_trend + model_c[k] * w_history), 1)
            for k in ("c", "m", "x")
        }

        single_class, single_prob = _class_from(single)
        dual_class, dual_prob = _class_from(dual)
        flare_class, prob = _class_from(multi)

        expected = datetime.now(timezone.utc) + timedelta(hours=hours)

        predictions.append(
            {
                "id": i + 1,
                "time_horizon": label,
                "hours_ahead": hours,
                "expected_time": expected.isoformat(),
                "flare_class": flare_class,
                "probability": round(prob, 3),
                "combined": multi,
                "single_model": {"flare_class": single_class, "probability": round(single_prob, 3), **single},
                "dual_model": {"flare_class": dual_class, "probability": round(dual_prob, 3), **dual},
                "models": {
                    "noaa_official": {k: round(v, 1) for k, v in model_a.items()},
                    "flux_trend": {k: round(v, 1) for k, v in model_b.items()},
                    "historical_frequency": {k: round(v, 1) for k, v in model_c.items()},
                },
                "weights": {"noaa_official": w_noaa, "flux_trend": w_trend, "historical_frequency": w_history},
            }
        )

    return {
        "predictions": predictions,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "data_source": summary["data_source"],
        "adaptive_weights_active": (w_noaa, w_trend, w_history) != (WEIGHT_NOAA, WEIGHT_TREND, WEIGHT_HISTORY),
        "methodology": (
            "Three tracked prediction variants, each recorded and verified against real NOAA outcomes "
            "separately: single-model (NOAA's own official active-region + SWPC outlook probabilities "
            "alone), dual-model (NOAA + live GOES flux-trend extrapolation, equally weighted), and "
            "multi-model (all 3 signals including historical C/M/X event frequency, blended with weights "
            "that adapt toward whichever variant has actually measured most accurate so far). This is a "
            "transparent statistical blend, not a trained machine-learning model — solar flare timing and "
            "magnitude cannot be predicted with certainty by any method."
        ),
    }
