"""
Combines live GOES X-ray flux (flare class), solar wind Kp-index, CME
earth-directed events, and NOAA's official Space Weather Scales into a single
plain-language "how this affects Earth" summary.
Source: https://services.swpc.noaa.gov/products/noaa-scales.json (NOAA's own
G/R/S scale + forecast, refreshed several times daily by SWPC forecasters).
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

NOAA_SCALES_URL = "https://services.swpc.noaa.gov/products/noaa-scales.json"
CACHE_TTL_SECONDS = 300

R_SCALE_EFFECTS = {
    "0": "No radio blackout impact.",
    "1": "Minor — weak degradation of HF radio on the sunlit side, occasional loss of radio contact.",
    "2": "Moderate — limited blackout of HF radio for tens of minutes, degraded low-frequency navigation signals.",
    "3": "Strong — wide-area blackout of HF radio for about an hour, navigation signals degraded for similar period.",
    "4": "Severe — HF radio blackout on most of the sunlit side for 1-2 hours, outages of low-frequency navigation.",
    "5": "Extreme — complete HF radio blackout on the sunlit side lasting a number of hours, navigation outages.",
}
S_SCALE_EFFECTS = {
    "0": "No radiation storm impact.",
    "1": "Minor — no biological impact; minor effects on satellite operations possible.",
    "2": "Moderate — infrequent single-event upsets to satellites possible, minor radiation exposure risk to polar-route aircrew/passengers.",
    "3": "Strong — radiation hazard to astronauts on EVA, satellite operations affected, elevated radiation for polar flights.",
    "4": "Severe — significant radiation risk to astronauts, satellite memory/orientation problems likely.",
    "5": "Extreme — unavoidable high radiation hazard to astronauts, complete blinding of satellite imagers, permanent satellite damage possible.",
}
G_SCALE_EFFECTS = {
    "0": "No geomagnetic storm impact.",
    "1": "Minor — weak power grid fluctuations, aurora visible at high latitudes.",
    "2": "Moderate — high-latitude power systems may see voltage alarms, aurora visible down to ~55° latitude.",
    "3": "Strong — voltage corrections needed on power systems, satellite orientation issues possible, aurora down to ~50° latitude.",
    "4": "Severe — widespread voltage control problems, possible grid system collapse, satellite tracking/navigation errors.",
    "5": "Extreme — power grid collapse or blackouts possible, satellite navigation and communication disrupted for days, aurora visible near the equator.",
}


class EarthImpactService:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()

    def _get_json(self, url: str) -> Any:
        # Fetch+parse must be inside the lock (not just cache access) — see
        # noaa_live_service.py for why: concurrent cron threads sharing one
        # requests.Session can otherwise race and corrupt reads.
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

    def fetch_noaa_scales(self) -> Dict[str, Any]:
        try:
            return self._get_json(NOAA_SCALES_URL) or {}
        except requests.RequestException as exc:
            logger.warning("NOAA scales fetch failed: %s", exc)
            return {}

    @staticmethod
    def _day_entry(scales: Dict[str, Any], offset: str, label: str) -> Dict[str, Any]:
        day = scales.get(offset, {})
        r = day.get("R", {}) or {}
        s = day.get("S", {}) or {}
        g = day.get("G", {}) or {}
        r_scale = r.get("Scale") or "0"
        s_scale = s.get("Scale") or "0"
        g_scale = g.get("Scale") or "0"
        return {
            "label": label,
            "date": day.get("DateStamp"),
            "radio_blackout": {"scale": r_scale, "text": r.get("Text") or "none", "effect": R_SCALE_EFFECTS.get(r_scale, "")},
            "radiation_storm": {"scale": s_scale, "text": s.get("Text") or "none", "effect": S_SCALE_EFFECTS.get(s_scale, "")},
            "geomagnetic_storm": {"scale": g_scale, "text": g.get("Text") or "none", "effect": G_SCALE_EFFECTS.get(g_scale, "")},
        }

    def build_summary(self) -> Dict[str, Any]:
        scales = self.fetch_noaa_scales()
        today = self._day_entry(scales, "0", "Today")
        forecast = [
            self._day_entry(scales, "1", "Day +1"),
            self._day_entry(scales, "2", "Day +2"),
            self._day_entry(scales, "3", "Day +3"),
        ]

        max_scale = max(
            int(today["radio_blackout"]["scale"]),
            int(today["radiation_storm"]["scale"]),
            int(today["geomagnetic_storm"]["scale"]),
        )
        if max_scale == 0:
            overall = "Quiet — no significant impact on Earth expected right now."
        elif max_scale <= 1:
            overall = "Minor — small effects possible on radio, satellites, or power systems."
        elif max_scale <= 2:
            overall = "Moderate — noticeable effects on high-latitude radio, navigation, and power systems possible."
        elif max_scale <= 3:
            overall = "Strong — significant disruption to radio communications, satellite operations, and power grids possible."
        else:
            overall = "Severe to extreme — widespread disruption to communications, navigation, satellites, and power grids likely."

        return {
            "data_source": "NOAA SWPC Space Weather Scales",
            "source_urls": [NOAA_SCALES_URL, "https://www.swpc.noaa.gov/noaa-scales-explanation"],
            "last_update": datetime.now(timezone.utc).isoformat(),
            "today": today,
            "forecast": forecast,
            "overall_earth_effect": overall,
            "max_scale_today": max_scale,
        }


earth_impact_service = EarthImpactService()
