"""
Live solar data from NOAA Space Weather Prediction Center (SWPC).
Source: https://services.swpc.noaa.gov/json/goes/primary/
Cross-validated against NOAA GOES X-ray flux products used by spaceweather.com and SWPC.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

NOAA_BASE = "https://services.swpc.noaa.gov/json"
GOES_PRIMARY = f"{NOAA_BASE}/goes/primary"
CACHE_TTL_SECONDS = 60

# GOES longwave (0.1-0.8 nm) flare class thresholds (W/m²)
FLARE_THRESHOLDS = {
    "A": 1e-8,
    "B": 1e-7,
    "C": 1e-6,
    "M": 1e-5,
    "X": 1e-4,
}

CLASS_MEANINGS = {
    "A": "Background level — no Earth impact.",
    "B": "Minor activity — negligible effects on Earth.",
    "C": "Small flare — may affect high-latitude radio at 1 GHz.",
    "M": "Medium flare — brief HF radio blackout in polar regions.",
    "X": "Major flare — widespread radio blackout and radiation storm risk.",
}


class NOAALiveService:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ISRO-Aditya-L1-Dashboard/1.0"})

    def _get_json(self, url: str) -> Any:
        # The fetch+parse must happen inside the lock too, not just the cache
        # dict access — cron jobs fire concurrently (APScheduler thread pool),
        # and concurrent .get() calls on one shared requests.Session could
        # otherwise interleave/corrupt reads, causing intermittent
        # "Extra data" JSON decode errors under concurrent load.
        with self._lock:
            now = time.time()
            if url in self._cache and now - self._cache_time.get(url, 0) < CACHE_TTL_SECONDS:
                return self._cache[url]

            response = self._session.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()

            self._cache[url] = data
            self._cache_time[url] = now
            return data

    @staticmethod
    def flux_to_class(flux: float) -> Tuple[str, str]:
        """Convert GOES longwave flux (W/m²) to flare class label e.g. C3.7."""
        if flux >= FLARE_THRESHOLDS["X"]:
            letter, base = "X", FLARE_THRESHOLDS["X"]
        elif flux >= FLARE_THRESHOLDS["M"]:
            letter, base = "M", FLARE_THRESHOLDS["M"]
        elif flux >= FLARE_THRESHOLDS["C"]:
            letter, base = "C", FLARE_THRESHOLDS["C"]
        elif flux >= FLARE_THRESHOLDS["B"]:
            letter, base = "B", FLARE_THRESHOLDS["B"]
        else:
            letter, base = "A", FLARE_THRESHOLDS["A"]
        multiplier = max(flux / base, 0.1)
        return letter, f"{letter}{multiplier:.1f}"

    @staticmethod
    def activity_level(flux: float) -> str:
        if flux >= 1e-4:
            return "Extreme"
        if flux >= 1e-5:
            return "High"
        if flux >= 1e-6:
            return "Moderate"
        if flux >= 1e-7:
            return "Low"
        return "Quiet"

    @staticmethod
    def risk_level(flux: float, m_prob: float) -> str:
        if flux >= 1e-4 or m_prob >= 70:
            return "critical"
        if flux >= 1e-5 or m_prob >= 40:
            return "medium"
        return "low"

    def fetch_xray_series(self, hours: int = 6) -> List[Dict[str, Any]]:
        url_map = {6: f"{GOES_PRIMARY}/xrays-6-hour.json", 24: f"{GOES_PRIMARY}/xrays-1-day.json", 168: f"{GOES_PRIMARY}/xrays-7-day.json"}
        url = url_map.get(hours, f"{GOES_PRIMARY}/xrays-6-hour.json")
        raw = self._get_json(url)

        short: Dict[str, float] = {}
        long: Dict[str, float] = {}
        for row in raw:
            tag = row["time_tag"]
            energy = row.get("energy", "")
            flux = float(row.get("flux") or 0)
            if energy == "0.05-0.4nm":
                short[tag] = flux
            elif energy == "0.1-0.8nm":
                long[tag] = flux

        points = []
        for tag in sorted(set(short) | set(long)):
            dt = datetime.fromisoformat(tag.replace("Z", "+00:00"))
            points.append(
                {
                    "time_tag": tag,
                    "time_label": dt.strftime("%H:%M"),
                    "shortwave_flux": short.get(tag, 0.0),
                    "longwave_flux": long.get(tag, 0.0),
                    "satellite": 18,
                }
            )
        return points

    def fetch_recent_flares(self) -> List[Dict[str, Any]]:
        raw = self._get_json(f"{GOES_PRIMARY}/xray-flares-7-day.json")
        flares = []
        for i, row in enumerate(sorted(raw, key=lambda r: r.get("max_time") or "", reverse=True)):
            flares.append(
                {
                    "id": i + 1,
                    "begin_time": row.get("begin_time"),
                    "max_time": row.get("max_time"),
                    "end_time": row.get("end_time"),
                    "begin_class": row.get("begin_class"),
                    "max_class": row.get("max_class"),
                    "end_class": row.get("end_class"),
                    "max_flux_wm2": float(row.get("max_xrlong") or 0),
                    "peak_intensity": row.get("max_class"),
                    "satellite": row.get("satellite", 18),
                    "duration_minutes": self._duration_minutes(row.get("begin_time"), row.get("end_time")),
                }
            )
        return flares

    def fetch_active_regions(self) -> List[Dict[str, Any]]:
        raw = self._get_json(f"{NOAA_BASE}/solar_regions.json")
        if not raw:
            return []
        latest_date = max(r.get("observed_date") or "" for r in raw)
        todays_rows = [r for r in raw if r.get("observed_date") == latest_date]

        # NOAA revises each day's region report through the day: rows start
        # as "d" (draft/provisional) and get superseded by "f" (final) later.
        # Only accepting "f" meant this returned zero regions for hours every
        # day until NOAA got around to finalizing — real region data (still
        # genuine NOAA numbers, just not yet marked final) sat unused, which
        # also silently zeroed out the NOAA-official signal in the flare
        # ensemble. Dedupe by region number, preferring the most-final status
        # available rather than requiring "f" specifically.
        status_rank = {"f": 2, "d": 1}
        best_by_region: Dict[Any, Dict[str, Any]] = {}
        for r in todays_rows:
            region_num = r.get("region")
            rank = status_rank.get(r.get("status"), 0)
            existing = best_by_region.get(region_num)
            if existing is None or rank > status_rank.get(existing.get("status"), 0):
                best_by_region[region_num] = r
        regions = list(best_by_region.values())
        # NOAA sends explicit `null` (not a missing key) for newly-rotating
        # regions not yet analyzed — dict.get(key, default) only substitutes
        # the default when the key is absent, so a `None` value here would
        # otherwise reach the sort comparison directly and crash comparing
        # int < NoneType. `or 0` catches both missing-key and explicit-None.
        regions.sort(key=lambda r: (r.get("m_flare_probability") or 0, r.get("area") or 0), reverse=True)
        result = []
        for r in regions:
            result.append(
                {
                    "region_number": r.get("region"),
                    "location": r.get("location"),
                    "latitude": r.get("latitude"),
                    "longitude": r.get("longitude"),
                    "area_millionths": r.get("area"),
                    "spot_class": r.get("spot_class"),
                    "magnetic_class": r.get("mag_class"),
                    "num_spots": r.get("number_spots"),
                    # NOAA sends explicit `null` (not a missing key) for these
                    # on unanalyzed regions — `.get(key, 0)` doesn't catch
                    # that, only `or 0` does. Downstream code (ensemble
                    # forecast, region ranking) assumes these are always
                    # numeric, so None here breaks in perhaps-surprising ways
                    # (int/NoneType comparisons, arithmetic on None) at the
                    # point of *use* rather than here, which made prior
                    # instances of this bug slow to trace back to this dict.
                    "c_probability_pct": r.get("c_flare_probability") or 0,
                    "m_probability_pct": r.get("m_flare_probability") or 0,
                    "x_probability_pct": r.get("x_flare_probability") or 0,
                    "c_events": r.get("c_xray_events") or 0,
                    "m_events": r.get("m_xray_events") or 0,
                    "x_events": r.get("x_xray_events") or 0,
                    "observed_date": r.get("observed_date"),
                    "intensity_score": self._region_intensity(r),
                }
            )
        return result

    def fetch_global_probabilities(self) -> Dict[str, Any]:
        raw = self._get_json(f"{NOAA_BASE}/solar_probabilities.json")
        return raw[-1] if raw else {}

    def fetch_background_flux(self) -> float:
        raw = self._get_json(f"{GOES_PRIMARY}/xray-background-7-day.json")
        if not raw:
            return 0.0
        return float(raw[-1].get("background") or 0)

    @staticmethod
    def _duration_minutes(begin: Optional[str], end: Optional[str]) -> Optional[int]:
        if not begin or not end:
            return None
        b = datetime.fromisoformat(begin.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return int((e - b).total_seconds() / 60)

    @staticmethod
    def _region_intensity(region: Dict[str, Any]) -> float:
        mag = region.get("mag_class") or ""
        mag_score = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}.get(mag[:1], 2)
        area = float(region.get("area") or 0)
        m_prob = float(region.get("m_flare_probability") or 0)
        m_events = int(region.get("m_xray_events") or 0)
        return round(mag_score * 10 + (area / 100) + m_prob * 0.5 + m_events * 5, 1)

    def _flux_trend(self, series: List[Dict[str, Any]], minutes: int = 30) -> float:
        if len(series) < 5:
            return 0.0
        recent = series[-minutes:] if len(series) >= minutes else series
        start = recent[0]["longwave_flux"]
        end = recent[-1]["longwave_flux"]
        if start <= 0:
            return 0.0
        return (end - start) / start

    def build_live_summary(self) -> Dict[str, Any]:
        series = self.fetch_xray_series(6)
        flares = self.fetch_recent_flares()
        regions = self.fetch_active_regions()
        global_prob = self.fetch_global_probabilities()
        background = self.fetch_background_flux()

        latest = series[-1] if series else {}
        long_flux = float(latest.get("longwave_flux", 0))
        short_flux = float(latest.get("shortwave_flux", 0))
        letter, class_label = self.flux_to_class(long_flux)
        trend = self._flux_trend(series)

        top_region = regions[0] if regions else None
        avg_m_prob = sum(r["m_probability_pct"] for r in regions[:5]) / max(len(regions[:5]), 1)

        latest_flare = flares[0] if flares else None

        return {
            "data_source": "NOAA SWPC GOES-18 X-ray Sensor (live)",
            "source_urls": [
                "https://www.swpc.noaa.gov/products/goes-x-ray-flux",
                "https://services.swpc.noaa.gov/json/goes/primary/",
            ],
            "last_update": latest.get("time_tag", datetime.now(timezone.utc).isoformat()),
            "satellite": latest.get("satellite", 18),
            "current_flux": {
                "shortwave_0_05_0_4_nm_wm2": short_flux,
                "longwave_0_1_0_8_nm_wm2": long_flux,
                "background_wm2": background,
                "shortwave_label": "GOES Short (0.05–0.4 nm) — coronal soft X-rays",
                "longwave_label": "GOES Long (0.1–0.8 nm) — flare classification band",
            },
            "current_class": class_label,
            "current_class_letter": letter,
            "class_meaning": CLASS_MEANINGS.get(letter, ""),
            "activity_level": self.activity_level(long_flux),
            "flux_trend_pct_30min": round(trend * 100, 2),
            "latest_flare": latest_flare,
            "recent_flares_count_7d": len(flares),
            "active_regions_count": len(regions),
            "top_active_region": top_region,
            "global_probabilities": global_prob,
            "risk_level": self.risk_level(long_flux, avg_m_prob),
        }

    def build_nowcast(self) -> Dict[str, Any]:
        summary = self.build_live_summary()
        long_flux = summary["current_flux"]["longwave_0_1_0_8_nm_wm2"]
        trend = summary["flux_trend_pct_30min"] / 100
        top = summary.get("top_active_region") or {}
        m_prob = (top.get("m_probability_pct") or 30) / 100

        # Automated nowcast: NOAA flux + region probability + short-term trend.
        # Bounded (min/max clamp) — unlike the old expected_peak field below,
        # this can't runaway from a transient trend spike.
        event_prob = min(0.98, max(0.05, m_prob + max(trend, 0) * 0.5 + (0.1 if long_flux >= 1e-6 else 0)))
        confidence = 0.92 if summary["satellite"] else 0.75

        # Real, data-driven duration estimate from actual recent flares —
        # replaces a previous hardcoded "15-90 minutes" string that claimed
        # to be data-driven but wasn't computed from anything.
        recent_durations = [f["duration_minutes"] for f in self.fetch_recent_flares() if f.get("duration_minutes")]
        if recent_durations:
            recent_durations.sort()
            n = len(recent_durations)
            median_dur = recent_durations[n // 2]
            p25 = recent_durations[max(0, n // 4)]
            p75 = recent_durations[min(n - 1, (3 * n) // 4)]
            expected_duration = f"{p25}–{p75} minutes (median {median_dur}, based on {n} real flares in the last 7 days)"
        else:
            expected_duration = "No recent flares to estimate duration from"

        explanation = (
            f"Live GOES-18 longwave flux is {summary['current_class']} ({long_flux:.2e} W/m²). "
            f"{summary['class_meaning']} "
        )
        if top:
            explanation += (
                f"Active Region {top['region_number']} ({top['location']}) shows "
                f"NOAA's published 24h probabilities: C={top.get('c_probability_pct', 0)}%, "
                f"M={top.get('m_probability_pct', 0)}%, X={top.get('x_probability_pct', 0)}%, "
                f"magnetic class {top['magnetic_class']}. "
            )
        if trend > 0.15:
            explanation += f"Flux rose {summary['flux_trend_pct_30min']:.1f}% in the last 30 minutes — elevated short-term flare risk. "
        elif trend < -0.15:
            explanation += f"Flux declined {abs(summary['flux_trend_pct_30min']):.1f}% in the last 30 minutes. "

        return {
            "current_flare_class": summary["current_class"],
            "current_activity_level": summary["activity_level"],
            "probability_of_current_event": round(event_prob, 3),
            "current_flux": long_flux,
            "shortwave_flux": summary["current_flux"]["shortwave_0_05_0_4_nm_wm2"],
            # NOAA's own published 24h class-threshold probabilities for the
            # dominant active region — real forecaster data, not a derived
            # guess. Deliberately NOT a single "expected peak magnitude" (the
            # previous expected_peak field): extrapolating a specific future
            # flux value from a 30-min trend during a flare's rise phase
            # systematically overshoots, since real flares rise then decay
            # rather than keep climbing at the observed rate — that's what
            # produced wildly wrong single-number predictions before.
            "c_class_probability_pct": top.get("c_probability_pct") or 0,
            "m_class_probability_pct": top.get("m_probability_pct") or 0,
            "x_class_probability_pct": top.get("x_probability_pct") or 0,
            "expected_duration": expected_duration,
            "affected_region": f"AR {top['region_number']} ({top['location']})" if top else "No dominant active region",
            "current_confidence": confidence,
            "ai_explanation": explanation,
            "risk_level": summary["risk_level"],
            "suggested_action": self._suggested_action(summary["risk_level"]),
            "last_update": summary["last_update"],
            "data_source": summary["data_source"],
        }

    @staticmethod
    def _suggested_action(risk: str) -> str:
        if risk == "critical":
            return "Alert operators — protect satellites, aviation polar routes, and HF comms"
        if risk == "medium":
            return "Monitor GOES flux and active regions continuously"
        return "Routine monitoring — conditions nominal"

    def build_forecast(self) -> Dict[str, Any]:
        summary = self.build_live_summary()
        regions = self.fetch_active_regions()
        global_prob = summary.get("global_probabilities") or {}
        trend = summary["flux_trend_pct_30min"] / 100

        avg_c = sum(r["c_probability_pct"] for r in regions[:8]) / max(len(regions[:8]), 1)
        avg_m = sum(r["m_probability_pct"] for r in regions[:8]) / max(len(regions[:8]), 1)
        avg_x = sum(r["x_probability_pct"] for r in regions[:8]) / max(len(regions[:8]), 1)

        horizons = [
            ("1 hour", 1 / 24, avg_c, avg_m, avg_x),
            ("6 hours", 6 / 24, avg_c, avg_m, avg_x),
            ("12 hours", 12 / 24, avg_c, avg_m, avg_x),
            ("24 hours", 1.0, global_prob.get("c_class_1_day", avg_c), global_prob.get("m_class_1_day", avg_m), global_prob.get("x_class_1_day", avg_x)),
            ("48 hours", 2.0, global_prob.get("c_class_2_day", avg_c), global_prob.get("m_class_2_day", avg_m), global_prob.get("x_class_2_day", avg_x)),
            ("72 hours", 3.0, global_prob.get("c_class_3_day", avg_c), global_prob.get("m_class_3_day", avg_m), global_prob.get("x_class_3_day", avg_x)),
        ]

        predictions = []
        for i, (label, day_frac, c_p, m_p, x_p) in enumerate(horizons):
            trend_boost = max(trend, 0) * 20 * (1 - day_frac)
            c_adj = min(99, c_p + trend_boost)
            m_adj = min(99, m_p + trend_boost * 0.6)
            x_adj = min(99, x_p + trend_boost * 0.3)

            if x_adj >= 15:
                flare_class, prob = "X", x_adj / 100
            elif m_adj >= 25:
                flare_class, prob = "M", m_adj / 100
            else:
                flare_class, prob = "C", c_adj / 100

            expected = datetime.now(timezone.utc) + timedelta(hours={"1 hour": 1, "6 hours": 6, "12 hours": 12, "24 hours": 24, "48 hours": 48, "72 hours": 72}[label])

            predictions.append(
                {
                    "id": i + 1,
                    "time_horizon": label,
                    "hours_ahead": {"1 hour": 1, "6 hours": 6, "12 hours": 12, "24 hours": 24, "48 hours": 48, "72 hours": 72}[label],
                    "flare_class": flare_class,
                    "probability": round(prob, 3),
                    "c_class_chance_pct": round(c_adj, 1),
                    "m_class_chance_pct": round(m_adj, 1),
                    "x_class_chance_pct": round(x_adj, 1),
                    "confidence": round(0.95 - day_frac * 0.08, 2),
                    "expected_time": expected.isoformat(),
                    "prediction_interval": label,
                    "model_used": "NOAA SWPC region probabilities + GOES flux trend",
                    "reasoning": f"C:{c_adj:.0f}% M:{m_adj:.0f}% X:{x_adj:.0f}% chance in next {label}",
                }
            )

        return {
            "predictions": predictions,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "data_source": summary["data_source"],
            "methodology": "Combines NOAA active-region flare probabilities, SWPC 1–3 day outlook, and live GOES flux trend.",
        }

    def build_alerts(self) -> Dict[str, Any]:
        summary = self.build_live_summary()
        flares = self.fetch_recent_flares()[:5]
        alerts = []
        long_flux = summary["current_flux"]["longwave_0_1_0_8_nm_wm2"]

        if long_flux >= 1e-5:
            alerts.append(
                {
                    "id": 1,
                    "timestamp": summary["last_update"],
                    "alert_level": "CRITICAL" if long_flux >= 1e-4 else "WARNING",
                    "alert_type": "M_CLASS_FLUX" if long_flux < 1e-4 else "X_CLASS_FLUX",
                    "reason": f"Live GOES flux at {summary['current_class']} ({long_flux:.2e} W/m²)",
                    "confidence": 0.99,
                    "acknowledged": False,
                }
            )

        for i, flare in enumerate(flares[:3]):
            max_class = flare.get("max_class", "?")
            level = "CRITICAL" if max_class.startswith("X") else "WARNING" if max_class.startswith("M") else "INFO"
            alerts.append(
                {
                    "id": i + 10,
                    "timestamp": flare.get("max_time", summary["last_update"]),
                    "alert_level": level,
                    "alert_type": f"FLARE_{max_class[0]}_CLASS",
                    "reason": f"Flare peaked at {max_class} ({flare.get('max_flux_wm2', 0):.2e} W/m²)",
                    "confidence": 0.99,
                    "acknowledged": True,
                }
            )

        top = summary.get("top_active_region")
        if top and top.get("m_probability_pct", 0) >= 50:
            alerts.append(
                {
                    "id": 99,
                    "timestamp": summary["last_update"],
                    "alert_level": "WARNING",
                    "alert_type": "HIGH_M_PROBABILITY_REGION",
                    "reason": f"AR {top['region_number']} ({top['location']}) M-class probability {top['m_probability_pct']}%",
                    "confidence": 0.85,
                    "acknowledged": False,
                }
            )

        active = [a for a in alerts if not a["acknowledged"]]
        return {
            "alerts": alerts,
            "total_active": len(active),
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "data_source": summary["data_source"],
        }

    def build_flux_history(self, hours: int = 6) -> List[Dict[str, Any]]:
        series = self.fetch_xray_series(hours if hours <= 24 else 168)
        return [
            {
                "time": p["time_label"],
                "time_tag": p["time_tag"],
                "soft": p["shortwave_flux"],
                "hard": p["longwave_flux"],
            }
            for p in series
        ]


noaa_live_service = NOAALiveService()
