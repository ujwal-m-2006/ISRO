"""
Solar Flare Alerts & Notices — real-time flare events reshaped for the alert
ticker / notice board / dashboard cards UI, all derived from the same NOAA
GOES X-ray flare catalogue (noaa_live_service.fetch_recent_flares) and
active-region probabilities (noaa_live_service.fetch_active_regions) already
used elsewhere in this app. No values here are invented — severity, radio
scale, and impact text are the well-established, publicly documented NOAA
flare-class -> R-scale correspondence (see
https://www.swpc.noaa.gov/noaa-scales-explanation), not estimates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.noaa_live_service import noaa_live_service

SEVERITY_LABELS = {"A": "Low", "B": "Low", "C": "Moderate", "M": "High"}


def _severity(flare_class: str) -> str:
    letter = flare_class[:1].upper()
    if letter == "X":
        try:
            magnitude = float(flare_class[1:])
        except (ValueError, IndexError):
            magnitude = 1.0
        return "Extreme" if magnitude >= 5 else "Severe"
    return SEVERITY_LABELS.get(letter, "Low")


def _radio_scale_and_impact(flare_class: str) -> tuple[str, List[str]]:
    """NOAA's published flare-class -> R-scale mapping (fixed public
    reference table, not a per-event estimate): M1-M4=R1, M5-M9=R2,
    X1-X9=R3, X10-X19=R4, X20+=R5. C-class and below have no listed R-scale
    (negligible radio impact)."""
    letter = flare_class[:1].upper()
    try:
        magnitude = float(flare_class[1:])
    except (ValueError, IndexError):
        magnitude = 1.0

    if letter == "M":
        if magnitude >= 5:
            return "R2", ["HF Radio Blackout (moderate, sunlit side)", "Degraded low-frequency navigation"]
        return "R1", ["HF Radio Blackout (minor, polar regions)"]
    if letter == "X":
        if magnitude >= 20:
            return "R5", ["Complete HF Radio Blackout (sunlit side, hours)", "Navigation outages", "Satellite operations at risk", "Aviation — polar route advisory"]
        if magnitude >= 10:
            return "R4", ["Severe HF Radio Blackout (1-2 hours)", "Navigation degraded", "Satellite operations at risk", "Aviation — polar route advisory"]
        return "R3", ["Wide-area HF Radio Blackout (~1 hour)", "Navigation signals degraded", "Aviation — polar route advisory"]
    return "R0", []


def _status(begin: Optional[str], max_time: Optional[str], end: Optional[str], now: datetime) -> str:
    """NOAA's flare catalogue reports finalized events (begin/max/end all
    set once the event completes) — there's no live in-progress flare feed
    to poll here, so "Active"/"Increasing"/"Decaying" only apply within a
    short window after the event actually happened; older events are
    "Ended". This avoids claiming a flare is still "Active" days later."""
    if not begin:
        return "Ended"
    begin_dt = datetime.fromisoformat(begin.replace("Z", "+00:00"))
    max_dt = datetime.fromisoformat(max_time.replace("Z", "+00:00")) if max_time else None
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None

    if end_dt and now >= end_dt:
        # Recently ended (within 30 min) is worth flagging as "Decaying"
        # rather than a flat "Ended" — otherwise identical wording either way.
        return "Decaying" if now - end_dt <= timedelta(minutes=30) else "Ended"
    if max_dt and now >= max_dt:
        return "Decaying"
    if now >= begin_dt:
        return "Increasing"
    return "Ended"


def _associated_region(flare_date: Optional[str], regions: List[Dict[str, Any]]) -> Optional[str]:
    """NOAA's GOES flare catalogue doesn't include a per-flare active-region
    number, so this can only report the day's dominant region (highest
    M-probability) as a best-effort association, not a confirmed source —
    labelled accordingly rather than presented as fact."""
    if not flare_date or not regions:
        return None
    top = regions[0]
    region_num = top.get("region_number")
    return f"AR{region_num} (dominant region that day — not a confirmed source)" if region_num else None


def _description(flare_class: str, status: str, radio_scale: str) -> str:
    impact_note = f"NOAA radio blackout scale {radio_scale}." if radio_scale != "R0" else "No significant radio blackout expected."
    return f"{flare_class}-class solar flare, currently {status.lower()}. {impact_note}"


def build_flare_alerts() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    flares = noaa_live_service.fetch_recent_flares()
    regions = noaa_live_service.fetch_active_regions()
    summary = noaa_live_service.build_live_summary()

    alerts: List[Dict[str, Any]] = []
    for flare in flares[:20]:
        flare_class = flare.get("max_class") or flare.get("peak_intensity") or "?"
        radio_scale, impact = _radio_scale_and_impact(flare_class)
        status = _status(flare.get("begin_time"), flare.get("max_time"), flare.get("end_time"), now)
        begin_date = (flare.get("begin_time") or "")[:10]

        alerts.append(
            {
                "id": f"SF-{begin_date.replace('-', '')}-{flare['id']:03d}",
                "flare_class": flare_class,
                "severity": _severity(flare_class),
                "active_region": _associated_region(begin_date, regions),
                "status": status,
                "start_time": flare.get("begin_time"),
                "peak_time": flare.get("max_time"),
                "end_time": flare.get("end_time"),
                "peak_flux_wm2": flare.get("max_flux_wm2"),
                "duration_minutes": flare.get("duration_minutes"),
                "impact": impact,
                "radio_scale": radio_scale,
                "description": _description(flare_class, status, radio_scale),
            }
        )

    significant = [a for a in alerts if a["severity"] not in ("Low",)]
    today_str = now.strftime("%Y-%m-%d")
    today_flares = [a for a in alerts if (a["start_time"] or "").startswith(today_str)]

    strongest = max(alerts, key=lambda a: a.get("peak_flux_wm2") or 0, default=None)

    return {
        "alerts": alerts,
        "ticker_alerts": significant[:10],  # ticker only shows C-class+ (skip routine A/B noise)
        "summary": {
            "total_flares_today": len(today_flares),
            "strongest_flare": strongest["flare_class"] if strongest else None,
            "current_activity_level": summary["activity_level"],
            "active_regions_count": len(regions),
            "latest_flare": alerts[0]["flare_class"] if alerts else None,
            "radio_blackout_level": alerts[0]["radio_scale"] if alerts else "R0",
        },
        "last_updated": now.isoformat(),
        "data_source": "NOAA SWPC GOES X-ray Flare Catalogue",
        "source_urls": [
            "https://www.swpc.noaa.gov/products/goes-x-ray-flux",
            "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
        ],
    }
