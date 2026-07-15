"""
Serves live predictions from the real, genuinely-fitted scikit-learn
classifiers trained by ml_models/train_flare_model.py — distinct from
flare_ensemble_service.py's transparent hand-weighted statistical blend.
These are actual models fit on real historical NOAA + Aditya-L1 data with
a held-out temporal test split; their reported accuracy comes from that
real test set, not asserted.

Honesty constraints this module enforces:
  - If no trained models exist yet (training hasn't been run), says so
    explicitly rather than returning nothing or fabricating a number.
  - dual_model / multi_model need a live Aditya-L1 feature to predict from.
    If PRADAN credentials aren't configured on this deployment (e.g. a
    Render env missing PRADAN_USERNAME/PASSWORD), those variants are
    reported as unavailable rather than silently falling back to
    NOAA-only and calling it a "dual model" prediction.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

SAVE_DIR = Path(__file__).resolve().parent.parent / "ml_models" / "saved"

_models: Dict[str, Any] = {}
_metadata: Optional[Dict[str, Any]] = None
_metadata_mtime: Optional[float] = None


def _load() -> None:
    """Re-reads metadata.json whenever its mtime changes, rather than a
    one-shot load — a long-running server process (this dev session hit
    this exact bug) would otherwise keep serving stale in-memory metadata
    from before a retrain, even though the file on disk has moved on."""
    global _metadata, _metadata_mtime
    meta_path = SAVE_DIR / "metadata.json"
    if not meta_path.exists():
        if _metadata_mtime is not None:  # only warn once per missing-file state
            return
        logger.warning("No trained model metadata found at %s — run `python -m ml_models.train_flare_model`", meta_path)
        _metadata_mtime = -1
        return

    current_mtime = meta_path.stat().st_mtime
    if current_mtime == _metadata_mtime:
        return
    _metadata_mtime = current_mtime

    with open(meta_path, encoding="utf-8") as f:
        _metadata = json.load(f)
    for name in ("single_model", "dual_model", "multi_model"):
        path = SAVE_DIR / f"{name}.joblib"
        if path.exists():
            _models[name] = joblib.load(path)


def _live_noaa_features() -> Optional[Dict[str, float]]:
    from services.noaa_live_service import noaa_live_service

    summary = noaa_live_service.build_live_summary()
    return {
        "noaa_flux": summary["current_flux"]["longwave_0_1_0_8_nm_wm2"],
        "noaa_flux_trend": summary["flux_trend_pct_30min"] / 100,
    }


def _live_adityal1_features() -> Optional[Dict[str, float]]:
    """Reads the cached real Aditya-L1 signal from job_fetch_adityal1_features
    (a periodic cron job that downloads + parses the latest available real
    SoLEXS light curve — see jobs/data_jobs.py). Downloading+parsing a full
    day's FITS file on every single prediction request would be far too
    slow for a live API call, so this is refreshed periodically instead of
    per-request; the returned dict includes its own timestamp so staleness
    is visible rather than hidden."""
    from services.job_store import job_store

    cached = job_store.load("adityal1_live_features", max_age_seconds=21600)  # 6h
    if not cached:
        return None
    return cached


def get_trained_predictions() -> Dict[str, Any]:
    _load()

    if _metadata is None:
        return {
            "available": False,
            "message": "No trained model exists yet — training has not been run on this deployment.",
            "variants": {},
        }

    noaa_features = _live_noaa_features()
    adityal1_features = _live_adityal1_features()
    result: Dict[str, Any] = {
        "available": True,
        "trained_at": _metadata["trained_at"],
        "training_window": _metadata["training_window"],
        "target": _metadata["target"],
        "daily_series": _metadata.get("daily_series", []),
        "variants": {},
    }

    for name, meta in _metadata.get("variants", {}).items():
        model = _models.get(name)
        entry: Dict[str, Any] = {
            "datasets": meta["datasets"],
            "test_accuracy": meta.get("test_accuracy"),
            "test_precision": meta.get("test_precision"),
            "test_recall": meta.get("test_recall"),
            "train_samples": meta.get("train_samples"),
            "test_samples": meta.get("test_samples"),
        }
        if model is None:
            entry["prediction_available"] = False
            entry["reason"] = "Model artifact missing on this deployment."
        elif name == "single_model":
            X = pd.DataFrame([noaa_features])[meta["features"]]
            proba = float(model.predict_proba(X)[0][1])
            entry["prediction_available"] = True
            entry["probability_pct"] = round(proba * 100, 1)
            entry["predicted_positive"] = proba >= 0.5
        elif adityal1_features is not None:
            combined = {**noaa_features, **adityal1_features}
            X = pd.DataFrame([combined])[meta["features"]]
            proba = float(model.predict_proba(X)[0][1])
            entry["prediction_available"] = True
            entry["probability_pct"] = round(proba * 100, 1)
            entry["predicted_positive"] = proba >= 0.5
            entry["adityal1_feature_as_of"] = adityal1_features.get("as_of")
        else:
            # dual_model / multi_model need a live Aditya-L1 feature this
            # deployment may not have (e.g. no PRADAN credentials on
            # Render, or the refresh cron hasn't completed one cycle yet)
            # — reported honestly rather than silently falling back to
            # NOAA-only and calling it a "dual model" prediction.
            entry["prediction_available"] = False
            entry["reason"] = "Live Aditya-L1 feature not available on this deployment (needs PRADAN credentials configured and the refresh cron to have run)."

        result["variants"][name] = entry

    return result
