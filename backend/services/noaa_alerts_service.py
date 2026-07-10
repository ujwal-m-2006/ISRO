"""
NOAA SWPC's live space weather bulletin feed (alerts.json) — real human-issued
forecaster alerts, always available (no API key, no rate limit like DONKI).
Used here for two things DONKI can't reliably provide when it's down:

  1. CME shock detection via Type II/IV radio burst alerts — these ARE the
     standard operational proxy for "a CME-driven shock has been detected",
     including an estimated velocity (km/s) straight from NOAA, which feeds
     directly into our Drag-Based Model arrival estimate.
  2. Geomagnetic storm WATCHES — NOAA's own forecasters issuing day-by-day
     G-scale predictions (e.g. "Jul 03: G2 (Moderate)"), which is literally
     "predicted storm, when, what intensity" from the authoritative source.

Source: https://services.swpc.noaa.gov/products/alerts.json
"""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from services.cme_arrival_service import estimate_arrival
from services.solar_wind_service import solar_wind_service

logger = logging.getLogger(__name__)

# How far apart two independent measurements of "the same event" can be and
# still plausibly be the same physical event, based on how each is derived:
FLARE_MATCH_WINDOW_HOURS = 3       # a CME-associated flare peaks close to the radio-burst onset
DONKI_MATCH_WINDOW_HOURS = 10      # DONKI's time21_5 is extrapolated to 21.5 solar radii, hours after actual liftoff

ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"
CACHE_TTL_SECONDS = 120

_TYPE_II_RE = re.compile(r"Type II Radio Emission")
_TYPE_IV_RE = re.compile(r"Type IV Radio Emission")
_VELOCITY_RE = re.compile(r"Estimate Velocity:\s*(\d+)\s*km/s")
_BEGIN_TIME_RE = re.compile(r"Begin Time:\s*(\d{4} \w{3} \d{2} \d{4}) UTC")
_WATCH_RE = re.compile(r"WATCH: Geomagnetic Storm Category (G\d) Predicted")
_DAY_LEVEL_RE = re.compile(r"(\w{3} \d{2}):\s*(None \(Below G1\)|G\d \([A-Za-z]+\))")


class NOAAAlertsService:
    def __init__(self) -> None:
        self._cache: Any = None
        self._cache_time: float = 0
        self._lock = threading.Lock()
        self._session = requests.Session()

    def fetch_alerts(self) -> List[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            if self._cache is not None and now - self._cache_time < CACHE_TTL_SECONDS:
                return self._cache
            try:
                resp = self._session.get(ALERTS_URL, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.warning("NOAA alerts fetch failed: %s", exc)
                return self._cache or []
            self._cache = data
            self._cache_time = now
            return data

    @staticmethod
    def _parse_noaa_time(text: str) -> str:
        """'2026 Jul 01 2257' -> ISO 8601 UTC."""
        dt = datetime.strptime(text, "%Y %b %d %H%M").replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def _find_associated_flare(begin_iso: str) -> Optional[Dict[str, Any]]:
        """Many CMEs are launched by an eruptive flare around the same time —
        cross-reference the real flare catalogue (not a guess) for one whose
        peak falls within a plausible window of this radio-burst detection."""
        from services.noaa_live_service import noaa_live_service

        try:
            begin_dt = datetime.fromisoformat(begin_iso)
        except ValueError:
            return None

        best = None
        best_diff = None
        for flare in noaa_live_service.fetch_recent_flares():
            peak = flare.get("max_time")
            if not peak:
                continue
            try:
                peak_dt = datetime.fromisoformat(peak.replace("Z", "+00:00"))
            except ValueError:
                continue
            diff_hours = abs((peak_dt - begin_dt).total_seconds()) / 3600
            if diff_hours > FLARE_MATCH_WINDOW_HOURS:
                continue
            if best_diff is None or diff_hours < best_diff:
                best_diff = diff_hours
                best = flare

        if not best:
            return None
        return {
            "flare_class": best.get("max_class"),
            "flare_peak_time": best.get("max_time"),
            "time_diff_minutes": round(best_diff * 60, 1),
        }

    @staticmethod
    def _find_donki_match(begin_iso: str) -> Optional[Dict[str, Any]]:
        """DONKI (coronagraph-based CME speed, measured on the CME's leading
        edge) and our Type II radio-burst speed (shock speed, measured low in
        the corona via radio drift rate) are different physical measurements
        of the same eruption and routinely disagree — sometimes by a lot.
        Surface both rather than picking one, so the difference is visible
        and explained instead of looking like an error."""
        from services.cme_service import cme_service

        try:
            begin_dt = datetime.fromisoformat(begin_iso)
        except ValueError:
            return None

        best = None
        best_diff = None
        try:
            donki_events = cme_service.fetch_recent_cmes(days=10)
        except Exception as exc:
            logger.warning("DONKI cross-check unavailable: %s", exc)
            return None

        for d in donki_events:
            start = d.get("start_time")
            if not start:
                continue
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except ValueError:
                continue
            diff_hours = abs((start_dt - begin_dt).total_seconds()) / 3600
            if diff_hours > DONKI_MATCH_WINDOW_HOURS:
                continue
            if best_diff is None or diff_hours < best_diff:
                best_diff = diff_hours
                best = d

        if not best:
            return None
        return {
            "donki_speed_km_s": best.get("speed_km_s"),
            "donki_start_time": best.get("start_time"),
            "donki_link": best.get("link"),
            "time_diff_hours": round(best_diff, 1),
        }

    def build_cme_indicators(self, days: int = 7) -> Dict[str, Any]:
        alerts = self.fetch_alerts()
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400

        wind_speed = None
        try:
            wind_speed = solar_wind_service.build_summary().get("speed_km_s")
        except Exception:
            pass

        events = []
        for a in alerts:
            msg = a.get("message", "")
            is_t2 = bool(_TYPE_II_RE.search(msg))
            is_t4 = bool(_TYPE_IV_RE.search(msg))
            if not (is_t2 or is_t4):
                continue

            begin_match = _BEGIN_TIME_RE.search(msg)
            if not begin_match:
                continue
            try:
                begin_iso = self._parse_noaa_time(begin_match.group(1))
            except ValueError:
                continue
            if datetime.fromisoformat(begin_iso).timestamp() < cutoff:
                continue

            velocity_match = _VELOCITY_RE.search(msg)
            velocity = float(velocity_match.group(1)) if velocity_match else None

            event: Dict[str, Any] = {
                "product_id": a.get("product_id"),
                "type": "Type II (shock)" if is_t2 else "Type IV",
                "begin_time": begin_iso,
                "velocity_km_s": velocity,
                "issued": a.get("issue_datetime"),
            }

            flare_match = self._find_associated_flare(begin_iso)
            if flare_match:
                event["associated_flare"] = flare_match

            donki_match = self._find_donki_match(begin_iso)
            if donki_match:
                event["donki_cross_check"] = donki_match
                if velocity and donki_match.get("donki_speed_km_s"):
                    diff_pct = abs(velocity - donki_match["donki_speed_km_s"]) / max(velocity, donki_match["donki_speed_km_s"]) * 100
                    donki_match["speed_difference_pct"] = round(diff_pct, 1)
                    donki_match["note"] = (
                        "NOAA radio-burst shock speed and NASA DONKI's coronagraph leading-edge speed "
                        "measure different physical features of the same eruption — disagreement here "
                        "is expected, not an error."
                    )

            if velocity and wind_speed:
                event["arrival_estimate"] = estimate_arrival(velocity, wind_speed, begin_iso)
            events.append(event)

        events.sort(key=lambda e: e["begin_time"], reverse=True)
        return {
            "data_source": "NOAA SWPC Space Weather Alerts (Type II/IV radio burst detections)",
            "source_urls": [ALERTS_URL, "https://www.swpc.noaa.gov/products/goes-x-ray-flux"],
            "window_days": days,
            "count": len(events),
            "events": events,
        }

    @staticmethod
    def parse_day_label(day_label: str, now: datetime) -> Optional[datetime]:
        """'Jul 03' has no year — assume current year, but if that lands more
        than ~180 days in the past, it's actually next year (handles the
        Dec/Jan boundary without needing real date context from the source)."""
        try:
            parsed = datetime.strptime(f"{now.year} {day_label}", "%Y %b %d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if (now - parsed).days > 180:
            parsed = parsed.replace(year=now.year + 1)
        return parsed

    def build_storm_watches(self) -> Dict[str, Any]:
        alerts = self.fetch_alerts()
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        watches = []
        for a in alerts:
            msg = a.get("message", "")
            watch_match = _WATCH_RE.search(msg)
            if not watch_match:
                continue

            days = []
            for day_label, level in _DAY_LEVEL_RE.findall(msg):
                days.append({"day": day_label, "level": level.strip()})

            # A watch is "current" only if at least one of its forecasted
            # days is today or later — otherwise it's a real historical
            # bulletin being mistaken for a live prediction, which is exactly
            # the confusing behavior being fixed here (a watch issued days
            # ago covering days that have already passed was being shown as
            # if it were still in effect).
            forecast_dates = [self.parse_day_label(d["day"], now) for d in days]
            is_current = any(fd is not None and fd >= today for fd in forecast_dates)

            watches.append(
                {
                    "product_id": a.get("product_id"),
                    "issued": a.get("issue_datetime"),
                    "peak_category": watch_match.group(1),
                    "daily_forecast": days,
                    "is_current": is_current,
                }
            )

        watches.sort(key=lambda w: w.get("issued") or "", reverse=True)
        current_watches = [w for w in watches if w["is_current"]]
        return {
            "data_source": "NOAA SWPC Geomagnetic Storm Watches (human forecaster issued)",
            "source_urls": [ALERTS_URL],
            "count": len(watches),
            "watches": watches[:10],
            "latest": watches[0] if watches else None,
            "latest_current": current_watches[0] if current_watches else None,
            "has_active_watch": len(current_watches) > 0,
        }


noaa_alerts_service = NOAAAlertsService()
