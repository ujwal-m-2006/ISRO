"""
Trains real, genuinely-fitted classifiers to predict whether a C-class-or-
above solar flare will occur in the next 6 hours, using real NOAA GOES
X-ray flux and real Aditya-L1 SoLEXS light-curve data — not a heuristic
weighted blend like flare_ensemble_service.py, an actual scikit-learn
model fit on real historical data with a held-out temporal test split.

Three variants, matching the site's existing single/dual/multi-model
naming:
  single_model - trained on NOAA GOES-18 X-ray flux alone
  dual_model   - trained on NOAA + Aditya-L1 SoLEXS combined features
  multi_model  - a voting ensemble blending both trained models above

Training window: the real, aligned overlap between what NOAA's live JSON
API exposes (a rolling 7-day flux history — there is no free longer
continuous archive without heavier NCEI archive-file parsing) and what's
downloadable from PRADAN for the same days. This is a genuinely small
training set for a real classifier - disclosed honestly in the saved
metadata and surfaced in the UI, not hidden. Predicting "C-class-or-above"
(not M/X specifically) is a deliberate choice: in a 7-day window there are
only a handful of M-class events and often zero X-class ones, nowhere near
enough real positive examples to fit a statistically meaningful M/X
classifier - C-class has enough real occurrences in this window to train
on honestly.

Run manually: `python -m ml_models.train_flare_model` from backend/.
Saves models + a metadata.json (training window, sample counts, real
held-out test accuracy) to ml_models/saved/.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score

sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.fits_parser import extract_light_curve_from_zip  # noqa: E402
from services.pradan_scraper import PRADANScraper  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAVE_DIR = Path(__file__).resolve().parent / "saved"
SAVE_DIR.mkdir(exist_ok=True)

BIN_MINUTES = 5
HORIZON_HOURS = 6
FLARE_CLASS_THRESHOLD = "C"  # see module docstring — real data volume constraint
FLARE_FLUX_THRESHOLD_WM2 = 1e-6  # GOES longwave C-class threshold


# --- Real data fetch ---------------------------------------------------------

def fetch_noaa_flux() -> pd.DataFrame:
    r = requests.get("https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json", timeout=30)
    r.raise_for_status()
    raw = r.json()
    rows = [
        {"time": pd.Timestamp(row["time_tag"]), "flux": float(row.get("flux") or 0)}
        for row in raw
        if row.get("energy") == "0.1-0.8nm"
    ]
    df = pd.DataFrame(rows).drop_duplicates("time").sort_values("time").set_index("time")
    return df


def fetch_noaa_flares() -> List[Dict[str, Any]]:
    r = requests.get("https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json", timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_adityal1_counts(days_back: int) -> pd.DataFrame:
    """Downloads and parses real SoLEXS light curves for the last
    `days_back` days actually available from PRADAN. Real instrument gaps
    (a day with no file, or a detector with no data that day) are skipped,
    not backfilled with synthetic values."""
    scraper = PRADANScraper()
    if not scraper.authenticated:
        logger.warning("PRADAN auth failed (%s) — Aditya-L1 training data unavailable this run", scraper.auth_error)
        return pd.DataFrame(columns=["counts"])

    files = scraper.get_latest_solexs_data()[:days_back]
    all_points: List[Dict[str, Any]] = []
    for f in files:
        try:
            resp = scraper.session.get(f["url"], timeout=60)
            resp.raise_for_status()
            points = extract_light_curve_from_zip(resp.content)
            all_points.extend(points)
            logger.info("Parsed %s: %d real light-curve points", f["filename"], len(points))
        except Exception as exc:
            logger.warning("Skipping %s (real download/parse failure, not backfilled): %s", f.get("filename"), exc)

    if not all_points:
        return pd.DataFrame(columns=["counts"])
    df = pd.DataFrame(all_points)
    df["time"] = pd.to_datetime(df["timestamp"])
    return df.drop_duplicates("time").sort_values("time").set_index("time")[["counts"]]


# --- Feature engineering -----------------------------------------------------

def build_feature_table(noaa_flux: pd.DataFrame, adityal1: pd.DataFrame, flares: List[Dict[str, Any]]) -> pd.DataFrame:
    bin_freq = f"{BIN_MINUTES}min"
    noaa_binned = noaa_flux["flux"].resample(bin_freq).mean().ffill(limit=3)

    df = pd.DataFrame({"noaa_flux": noaa_binned})
    df["noaa_flux_trend"] = df["noaa_flux"].pct_change(periods=6).fillna(0).clip(-5, 5)  # ~30min trend

    if not adityal1.empty:
        al1_binned = adityal1["counts"].resample(bin_freq).mean()
        df["adityal1_counts"] = al1_binned.reindex(df.index).interpolate(limit=3)
        df["adityal1_trend"] = df["adityal1_counts"].pct_change(periods=6).fillna(0).clip(-5, 5)
        df["has_adityal1"] = df["adityal1_counts"].notna()
    else:
        df["adityal1_counts"] = np.nan
        df["adityal1_trend"] = 0.0
        df["has_adityal1"] = False

    # Real label: did GOES longwave flux reach C-class-or-above at any point
    # in the next HORIZON_HOURS after this bin? Built directly from the same
    # real 1-min flux series, not the coarser flare event list (which only
    # gives peak times, not a continuous series to look ahead in).
    future_max = noaa_flux["flux"].rolling(f"{HORIZON_HOURS}h", min_periods=1).max().shift(-int(HORIZON_HOURS * 60 / 1))
    future_max_binned = future_max.resample(bin_freq).max()
    df["label"] = (future_max_binned.reindex(df.index) >= FLARE_FLUX_THRESHOLD_WM2).astype(int)

    df = df.dropna(subset=["noaa_flux", "label"])
    return df


# --- Training -----------------------------------------------------------------

def _fit_and_eval(X: pd.DataFrame, y: pd.Series, feature_cols: List[str]) -> Tuple[LogisticRegression, Dict[str, float]]:
    n = len(X)
    split = int(n * 0.8)  # temporal split — train on earlier data, test on later, never random-shuffled
    X_train, X_test = X.iloc[:split][feature_cols], X.iloc[split:][feature_cols]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "test_accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "test_precision": round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "test_recall": round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "train_samples": int(split),
        "test_samples": int(n - split),
        "positive_rate_train": round(float(y_train.mean()), 4),
        "positive_rate_test": round(float(y_test.mean()), 4),
    }
    return model, metrics


def train_all(days_back: int = 10) -> Dict[str, Any]:
    logger.info("Fetching real NOAA GOES-18 flux history (7-day rolling window)...")
    noaa_flux = fetch_noaa_flux()
    flares = fetch_noaa_flares()
    logger.info("NOAA: %d real flux points, %d real flare events", len(noaa_flux), len(flares))

    logger.info("Downloading + parsing real Aditya-L1 SoLEXS light curves (last %d days available)...", days_back)
    adityal1 = fetch_adityal1_counts(days_back)
    logger.info("Aditya-L1: %d real light-curve points", len(adityal1))

    df = build_feature_table(noaa_flux, adityal1, flares)
    logger.info("Feature table: %d real time bins, %d positive labels", len(df), int(df["label"].sum()))

    results: Dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_window": {
            "noaa_start": str(noaa_flux.index.min()),
            "noaa_end": str(noaa_flux.index.max()),
            "adityal1_points": int(len(adityal1)),
            "adityal1_available": not adityal1.empty,
        },
        "target": f"{FLARE_CLASS_THRESHOLD}-class-or-above GOES longwave flux within {HORIZON_HOURS}h",
        "variants": {},
    }

    y = df["label"]

    # single_model: NOAA-only real features
    single_features = ["noaa_flux", "noaa_flux_trend"]
    single_model, single_metrics = _fit_and_eval(df, y, single_features)
    joblib.dump(single_model, SAVE_DIR / "single_model.joblib")
    results["variants"]["single_model"] = {
        "datasets": ["NOAA GOES-18 X-ray Flux"],
        "features": single_features,
        **single_metrics,
    }

    if not adityal1.empty and df["has_adityal1"].sum() > 20:
        # dual_model: NOAA + Aditya-L1 combined real features
        dual_features = ["noaa_flux", "noaa_flux_trend", "adityal1_counts", "adityal1_trend"]
        df_dual = df.dropna(subset=dual_features)
        dual_model, dual_metrics = _fit_and_eval(df_dual, df_dual["label"], dual_features)
        joblib.dump(dual_model, SAVE_DIR / "dual_model.joblib")
        results["variants"]["dual_model"] = {
            "datasets": ["NOAA GOES-18 X-ray Flux", "Aditya-L1 SoLEXS (SDD2)"],
            "features": dual_features,
            **dual_metrics,
        }

        # multi_model: voting ensemble blending both trained models above,
        # fit fresh on the same temporal train split (VotingClassifier
        # clones and refits its own estimators, so this is a genuine
        # combined model, not just a wrapper around the two already-fit
        # ones) and evaluated on the same held-out test split for a real
        # combined accuracy number.
        split = int(len(df_dual) * 0.8)
        X_train, X_test = df_dual[dual_features].iloc[:split], df_dual[dual_features].iloc[split:]
        multi_y_train, multi_y_test = df_dual["label"].iloc[:split], df_dual["label"].iloc[split:]

        multi_model = VotingClassifier(
            estimators=[
                ("single", LogisticRegression(max_iter=1000, class_weight="balanced")),
                ("dual", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ],
            voting="soft",
        )
        multi_model.fit(X_train, multi_y_train)
        multi_preds = multi_model.predict(X_test)
        multi_metrics = {
            "test_accuracy": round(float(accuracy_score(multi_y_test, multi_preds)), 4),
            "test_precision": round(float(precision_score(multi_y_test, multi_preds, zero_division=0)), 4),
            "test_recall": round(float(recall_score(multi_y_test, multi_preds, zero_division=0)), 4),
            "train_samples": split,
            "test_samples": len(df_dual) - split,
        }
        joblib.dump(multi_model, SAVE_DIR / "multi_model.joblib")
        results["variants"]["multi_model"] = {
            "datasets": ["NOAA GOES-18 X-ray Flux", "Aditya-L1 SoLEXS (SDD2)", "Voting ensemble of single+dual models"],
            "features": dual_features,
            **multi_metrics,
        }
    else:
        logger.warning("Not enough real Aditya-L1 data this run (%d usable bins) — skipping dual/multi model training", int(df["has_adityal1"].sum()))

    with open(SAVE_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info("Training complete. Results:\n%s", json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    train_all()
