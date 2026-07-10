"""
CME Earth-arrival time estimation using the Drag-Based Model (DBM) —
Vrsnak et al. 2013, "Propagation of Interplanetary Coronal Mass Ejections:
The Drag-Based Model" (Solar Physics 285). This is a real, published
space-weather technique for first-order CME transit-time estimates (used by
operational tools like the community DBM webtool at dbm.ufe.cz), not a
from-scratch invention — but it IS an approximation: real CME arrival
depends on 3D structure, interactions with other CMEs, and solar wind
conditions along the whole path that a single drag coefficient can't fully
capture. Typical DBM accuracy in the literature is roughly +/-10 hours, which
is why this returns a time window (varying the drag coefficient across its
plausible range) rather than one precise timestamp.

Physics: the CME decelerates/accelerates towards the ambient solar wind
speed under a drag force proportional to (v-w)*|v-w|. Closed-form solution:
  sign = +1 if v0 >= w else -1
  dv0  = abs(v0 - w)
  r(t) = r0 + w*t + (sign/gamma) * ln(1 + gamma*dv0*t)
  v(t) = w + sign*dv0 / (1 + gamma*dv0*t)
Solved numerically for t where r(t) crosses 1 AU (monotonic in t, so simple
bisection is reliable and exact enough for this purpose).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

SOLAR_RADIUS_KM = 696_000.0
R0_KM = 20 * SOLAR_RADIUS_KM  # ~20 Rs, the standard DBM starting distance
AU_KM = 149_597_870.7

# Plausible drag-coefficient range from the DBM literature (km^-1), used to
# produce an early/nominal/late arrival window rather than a false-precision
# single timestamp.
GAMMA_LOW = 0.1e-7
GAMMA_NOMINAL = 0.2e-7
GAMMA_HIGH = 0.5e-7


def _distance_at(t_seconds: float, v0: float, w: float, gamma: float) -> float:
    dv0 = v0 - w
    sign = 1.0 if dv0 >= 0 else -1.0
    adv0 = abs(dv0)
    if adv0 < 1e-6:
        return R0_KM + w * t_seconds
    return R0_KM + w * t_seconds + (sign / gamma) * math.log(1 + gamma * adv0 * t_seconds)


def _solve_arrival_seconds(v0: float, w: float, gamma: float, target_km: float = AU_KM) -> Optional[float]:
    if v0 <= 0:
        return None
    lo, hi = 0.0, 24 * 3600.0
    # Expand hi until it brackets the target distance (CME must eventually
    # reach 1 AU as long as it's moving; cap the search to avoid runaway loops)
    for _ in range(40):
        if _distance_at(hi, v0, w, gamma) >= target_km:
            break
        hi *= 1.5
    else:
        return None  # never reaches — implausible input, don't fabricate a time

    for _ in range(60):
        mid = (lo + hi) / 2
        if _distance_at(mid, v0, w, gamma) < target_km:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def estimate_arrival(cme_speed_km_s: float, solar_wind_speed_km_s: float, launch_time_iso: Optional[str] = None) -> Dict[str, Any]:
    """Returns an early/nominal/late arrival time window for a CME, given its
    initial speed and current ambient solar wind speed."""
    w = solar_wind_speed_km_s or 400.0  # typical slow-wind fallback if live data unavailable

    results = {}
    for label, gamma in (("earliest", GAMMA_HIGH), ("nominal", GAMMA_NOMINAL), ("latest", GAMMA_LOW)):
        seconds = _solve_arrival_seconds(cme_speed_km_s, w, gamma)
        results[label] = seconds

    if any(v is None for v in results.values()):
        return {
            "estimable": False,
            "reason": "CME speed too low relative to solar wind speed for the drag model to converge — no reliable arrival estimate.",
        }

    launch_dt = datetime.fromisoformat(launch_time_iso.replace("Z", "+00:00")) if launch_time_iso else datetime.now(timezone.utc)

    def to_arrival(seconds: float) -> Dict[str, Any]:
        arrival_dt = launch_dt + timedelta(seconds=seconds)
        return {"hours_after_launch": round(seconds / 3600, 1), "arrival_time": arrival_dt.isoformat()}

    # earliest gamma (highest drag) actually decelerates fastest -> could arrive later or earlier
    # depending on whether CME is faster or slower than wind; sort by actual transit time for clarity
    ordered = sorted(results.items(), key=lambda kv: kv[1])
    fastest_label, fastest_secs = ordered[0]
    slowest_label, slowest_secs = ordered[-1]
    nominal_secs = results["nominal"]

    return {
        "estimable": True,
        "model": "Drag-Based Model (Vrsnak et al. 2013)",
        "inputs": {
            "cme_speed_km_s": cme_speed_km_s,
            "ambient_solar_wind_speed_km_s": w,
            "r0_km": R0_KM,
            "target_distance_km": AU_KM,
        },
        "nominal": to_arrival(nominal_secs),
        "earliest_plausible": to_arrival(fastest_secs),
        "latest_plausible": to_arrival(slowest_secs),
        "uncertainty_note": (
            "DBM transit-time estimates are typically accurate to roughly +/-10 hours in "
            "published validation studies — treat this as a plausible window, not an exact time. "
            "Real arrival also depends on CME 3D structure and interactions not captured here."
        ),
    }
