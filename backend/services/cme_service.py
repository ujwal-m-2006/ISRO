"""
Coronal Mass Ejection (CME) tracking via NASA's DONKI (Space Weather Database
Of Notifications, Knowledge, Information) API.
Source: https://api.nasa.gov/DONKI/CME and https://api.nasa.gov/DONKI/CMEAnalysis

Requires a free NASA API key (https://api.nasa.gov/#signUp — instant signup,
email only). Falls back to the shared DEMO_KEY (rate-limited to 30 req/hr)
when NASA_API_KEY isn't set. DONKI has occasional upstream outages (returns
503 from NASA's own API gateway) — this service degrades gracefully when that
happens rather than failing the whole page.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from services.cme_arrival_service import estimate_arrival
from services.solar_wind_service import solar_wind_service

logger = logging.getLogger(__name__)

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
DONKI_BASE = "https://api.nasa.gov/DONKI"
CACHE_TTL_SECONDS = 300


class CMEService:
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

    def fetch_recent_cmes(self, days: int = 7) -> List[Dict[str, Any]]:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=days)
        url = f"{DONKI_BASE}/CMEAnalysis?startDate={start}&endDate={end}&mostAccurateOnly=true&api_key={NASA_API_KEY}"

        try:
            raw = self._get_json(url)
        except requests.RequestException as exc:
            logger.warning("DONKI CME fetch failed (upstream unavailable): %s", exc)
            return []

        events = []
        for row in raw or []:
            events.append(
                {
                    "id": row.get("cmeID") or row.get("catalog"),
                    "start_time": row.get("time21_5"),
                    "speed_km_s": row.get("speed"),
                    "type": row.get("type"),
                    "is_most_accurate": row.get("isMostAccurate"),
                    "latitude": row.get("latitude"),
                    "longitude": row.get("longitude"),
                    "half_angle_deg": row.get("halfAngle"),
                    "earth_directed": bool(row.get("enlilList")),
                    "note": row.get("note"),
                    "link": row.get("link"),
                }
            )
        events.sort(key=lambda e: e.get("start_time") or "", reverse=True)
        return events

    def build_summary(self, days: int = 7) -> Dict[str, Any]:
        events = self.fetch_recent_cmes(days)
        earth_directed = [e for e in events if e["earth_directed"]]
        note = None
        if not events:
            # Distinguish "no CMEs this week" from "DONKI unreachable" isn't possible
            # from an empty list alone, so surface the source status explicitly.
            note = "No CME events returned — either a quiet period or DONKI is temporarily unavailable."

        wind_speed = None
        try:
            wind_speed = solar_wind_service.build_summary().get("speed_km_s")
        except Exception as exc:
            logger.warning("Could not fetch live solar wind speed for CME arrival estimate: %s", exc)

        annotated_events = []
        for e in events[:15]:
            event = dict(e)
            if e["earth_directed"] and e.get("speed_km_s"):
                event["arrival_estimate"] = estimate_arrival(
                    cme_speed_km_s=e["speed_km_s"],
                    solar_wind_speed_km_s=wind_speed or 400.0,
                    launch_time_iso=e.get("start_time"),
                )
            annotated_events.append(event)

        return {
            "data_source": "NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information)",
            "source_urls": [f"{DONKI_BASE}/CMEAnalysis", "https://ccmc.gsfc.nasa.gov/donki/"],
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "window_days": days,
            "total_cmes": len(events),
            "earth_directed_count": len(earth_directed),
            "events": annotated_events,
            "note": note,
            "api_key_mode": "custom" if NASA_API_KEY != "DEMO_KEY" else "DEMO_KEY (rate-limited, set NASA_API_KEY for higher limits)",
        }


cme_service = CMEService()
