"""
Live solar wind from NOAA SWPC's propagated solar wind product (source: DSCOVR
spacecraft at L1, propagated to Earth's bow shock). This is the modern
successor to NOAA's historical ACE real-time solar wind feed — same role
(upstream solar wind monitor at L1) that all "solar wind" dashboards use.
Source: https://services.swpc.noaa.gov/products/geospace/propagated-solar-wind-1-hour.json
Also pulls the planetary K-index (geomagnetic activity) from the same agency.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

NOAA_BASE = "https://services.swpc.noaa.gov"
SOLAR_WIND_URL = f"{NOAA_BASE}/products/geospace/propagated-solar-wind-1-hour.json"
KP_INDEX_URL = f"{NOAA_BASE}/json/planetary_k_index_1m.json"
CACHE_TTL_SECONDS = 60


class SolarWindService:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ISRO-Aditya-L1-Dashboard/1.0"})

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

    def fetch_solar_wind_series(self) -> List[Dict[str, Any]]:
        """Propagated solar wind is returned as [header_row, *data_rows]."""
        raw = self._get_json(SOLAR_WIND_URL)
        if not raw or len(raw) < 2:
            return []
        header = raw[0]
        idx = {name: i for i, name in enumerate(header)}

        points = []
        for row in raw[1:]:
            def val(key: str) -> Any:
                i = idx.get(key)
                return row[i] if i is not None and i < len(row) else None

            points.append(
                {
                    "time_tag": val("time_tag"),
                    "propagated_time_tag": val("propagated_time_tag"),
                    "speed_km_s": val("speed"),
                    "density_p_cm3": val("density"),
                    "temperature_k": val("temperature"),
                    "bx_nt": val("bx"),
                    "by_nt": val("by"),
                    "bz_nt": val("bz"),
                    "bt_nt": val("bt"),
                }
            )
        return points

    def fetch_kp_index(self) -> List[Dict[str, Any]]:
        raw = self._get_json(KP_INDEX_URL)
        return raw or []

    @staticmethod
    def kp_activity_label(kp: float) -> str:
        if kp >= 7:
            return "Severe geomagnetic storm conditions"
        if kp >= 5:
            return "Geomagnetic storm conditions"
        if kp >= 4:
            return "Active"
        return "Quiet to unsettled"

    def build_summary(self) -> Dict[str, Any]:
        series = self.fetch_solar_wind_series()
        kp_series = self.fetch_kp_index()

        latest = series[-1] if series else {}
        latest_kp = kp_series[-1] if kp_series else {}
        kp_value = float(latest_kp.get("kp_index", latest_kp.get("estimated_kp", 0)) or 0)

        bz = latest.get("bz_nt")
        bz_south = bz is not None and bz < -5

        return {
            "data_source": "NOAA SWPC Propagated Solar Wind (DSCOVR @ L1) — ACE-heritage product",
            "source_urls": [SOLAR_WIND_URL, KP_INDEX_URL],
            "last_update": latest.get("time_tag", datetime.now(timezone.utc).isoformat()),
            "speed_km_s": latest.get("speed_km_s"),
            "density_p_cm3": latest.get("density_p_cm3"),
            "temperature_k": latest.get("temperature_k"),
            "bz_nt": bz,
            "bt_nt": latest.get("bt_nt"),
            "bz_south_alert": bz_south,
            "kp_index": kp_value,
            "kp_activity": self.kp_activity_label(kp_value),
            "kp_last_update": latest_kp.get("time_tag"),
        }

    def build_history(self) -> List[Dict[str, Any]]:
        return self.fetch_solar_wind_series()


solar_wind_service = SolarWindService()
