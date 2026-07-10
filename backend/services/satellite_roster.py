"""
Roster of Aditya-L1's seven payloads. Real-time telemetry from these
instruments is not publicly available (PRADAN requires personal registration
and only serves processed archival data, not a live feed). Where a NOAA/NASA
public feed measures the same physical quantity, we label it plainly as a
proxy rather than pretending it's Aditya-L1 data — but where PRADAN's own
archive is reachable (confirmed for all 7 payloads via authenticated
scraping), archive_available/archive_count reflect the real backfilled
catalogue from services/pradan_history.py, not a placeholder.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ADITYA_L1_PAYLOADS: List[Dict[str, Any]] = [
    {
        "code": "VELC",
        "pradan_ids": ["velc"],
        "name": "Visible Emission Line Coronagraph",
        "measures": "Solar corona imaging & CME initiation, coronal magnetic field diagnostics",
        "proxy_available": False,
        "proxy_source": None,
        "note": "No public real-time equivalent feed — but PRADAN's own archive is browsable below.",
    },
    {
        "code": "SUIT",
        "pradan_ids": ["suit"],
        "name": "Solar Ultraviolet Imaging Telescope",
        "measures": "Near-UV images of the photosphere and chromosphere (200-400 nm)",
        "proxy_available": False,
        "proxy_source": None,
        "note": "No public real-time equivalent feed — but PRADAN's own archive is browsable below.",
    },
    {
        "code": "SoLEXS",
        "pradan_ids": ["solexs"],
        "name": "Solar Low Energy X-ray Spectrometer",
        "measures": "Soft X-ray flux, 1-22 keV — solar flare monitoring",
        "proxy_available": True,
        "proxy_source": "NOAA GOES-18 XRS shortwave channel (0.05-0.4 nm)",
        "note": "Same physical measurement (soft X-ray flux), different satellite.",
    },
    {
        "code": "HEL1OS",
        "pradan_ids": ["hel1os"],
        "name": "High Energy L1 Orbiting X-ray Spectrometer",
        "measures": "Hard X-ray flux, 10-150 keV — solar flare hard X-ray monitoring",
        "proxy_available": True,
        "proxy_source": "NOAA GOES-18 XRS longwave channel (0.1-0.8 nm)",
        "note": "Proxy band is softer than HEL1OS's true hard X-ray range, but tracks the same flare events and classification.",
    },
    {
        "code": "ASPEX",
        "pradan_ids": ["swis", "steps"],
        "name": "Aditya Solar wind Particle Experiment (SWIS + STEPS sub-sensors)",
        "measures": "Solar wind protons & alpha particles (SWIS), supra-thermal & energetic particles (STEPS)",
        "proxy_available": True,
        "proxy_source": "NOAA propagated solar wind (DSCOVR @ L1) — speed, density, temperature",
        "note": "Same plasma parameters, different L1 spacecraft.",
    },
    {
        "code": "PAPA",
        "pradan_ids": ["papa"],
        "name": "Plasma Analyser Package for Aditya",
        "measures": "Solar wind electron distribution",
        "proxy_available": False,
        "proxy_source": None,
        "note": "No public real-time electron-distribution feed — but PRADAN's own archive is browsable below.",
    },
    {
        "code": "Magnetometer",
        "pradan_ids": ["mag"],
        "name": "Aditya-L1 Magnetometer",
        "measures": "Interplanetary magnetic field at L1",
        "proxy_available": True,
        "proxy_source": "NOAA propagated solar wind (DSCOVR @ L1) — Bx/By/Bz/Bt",
        "note": "Same measurement (IMF at L1), different spacecraft.",
    },
]


def get_roster(pradan_history_instruments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    history = pradan_history_instruments or {}
    payloads = []
    for p in ADITYA_L1_PAYLOADS:
        payload = dict(p)
        total_count = 0
        earliest = None
        latest = None
        for pid in p["pradan_ids"]:
            inst = history.get(pid)
            if not inst:
                continue
            summary = inst.get("summary", {})
            total_count += summary.get("count", 0)
            if summary.get("earliest") and (earliest is None or summary["earliest"] < earliest):
                earliest = summary["earliest"]
            if summary.get("latest") and (latest is None or summary["latest"] > latest):
                latest = summary["latest"]

        payload["archive_available"] = total_count > 0
        payload["archive_file_count"] = total_count
        payload["archive_earliest"] = earliest
        payload["archive_latest"] = latest
        payloads.append(payload)

    return {
        "mission": "Aditya-L1",
        "agency": "ISRO",
        "payload_count": len(payloads),
        "payloads": payloads,
        "proxied_count": sum(1 for p in payloads if p["proxy_available"]),
        "archived_count": sum(1 for p in payloads if p["archive_available"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclosure": (
            "Aditya-L1 does not publish a public real-time data API. Instruments marked "
            "proxy_available use live data from equivalent NOAA/NASA instruments measuring "
            "the same physical quantity. All 7 payloads' real historical archives are "
            "reachable via PRADAN (pradan1.issdc.gov.in) once authenticated — archive_available "
            "reflects the actual backfilled file catalogue, not a placeholder. SoLEXS, HEL1OS, "
            "PAPA, and the Magnetometer have their full mission history (only a few thousand "
            "files each). VELC, SUIT, and ASPEX's SWIS/STEPS sub-sensors image far more "
            "frequently (VELC alone exceeds 20,000 files) — backfilling their entire multi-year "
            "archive would mean tens of thousands of requests against a live government server, "
            "so those show a capped recent window (~1,500 most recent files) instead."
        ),
    }
