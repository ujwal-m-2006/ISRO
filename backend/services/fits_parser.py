"""
Parses real Aditya-L1 SoLEXS light-curve FITS files from PRADAN.

Verified against an actual downloaded file
(AL1_SLX_L1_20260712_v1.0/SDD2/AL1_SOLEXS_20260712_SDD2_L1.lc): each daily
archive is a zip containing per-detector (SDD1/SDD2) gzipped FITS files —
.lc (light curve: the count-rate-vs-time data used here), .pi (spectrum),
.gti (good time intervals). The light curve's HDU1 ("RATE") is a binary
table with exactly two columns:
    TIME   - Unix epoch seconds (confirmed via MJDREFI=40587, the Unix
             epoch in Modified Julian Date, and cross-checked against the
             file's own DATE-OBS header)
    COUNTS - raw photon counts in that time bin (NaN for gaps)
1-second cadence, ~86400 rows per day. SDD1 is not always present (real
instrument data gaps) — SDD2 is used as the primary channel.

The previous version of this file computed a blind mean/sum over whatever
array happened to be in the primary HDU, which does not match this file's
real structure (a binary table in HDU1, not primary-HDU image data) — it
was never actually tested against a real file.
"""

from __future__ import annotations

import gzip
import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
from astropy.io import fits

logger = logging.getLogger(__name__)


def _open_fits_bytes(raw: bytes) -> fits.HDUList:
    """PRADAN serves these gzipped — transparently handle both gzipped and
    plain FITS bytes."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return fits.open(io.BytesIO(raw))


def parse_light_curve(raw: bytes) -> List[Dict[str, Any]]:
    """Parses a SoLEXS/HEL1OS .lc(.gz) file's RATE table into a list of
    {timestamp, counts} points, skipping NaN gaps."""
    with _open_fits_bytes(raw) as hdul:
        table = hdul["RATE"].data
        times = table["TIME"]
        counts = table["COUNTS"]

    points = []
    for t, c in zip(times, counts):
        if np.isnan(c):
            continue
        points.append(
            {
                "timestamp": datetime.fromtimestamp(float(t), tz=timezone.utc).isoformat(),
                "counts": float(c),
            }
        )
    return points


def extract_light_curve_from_zip(zip_bytes: bytes, prefer_detector: str = "SDD2") -> List[Dict[str, Any]]:
    """A daily PRADAN archive is a zip of per-detector subfolders, each with
    a gzipped .lc file. Real instrument data gaps mean a given detector
    isn't always present for a given day (confirmed: SDD1 was entirely
    absent from one real archive checked) — falls back to whichever
    detector's .lc file is actually present rather than assuming both are."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        lc_names = [n for n in z.namelist() if n.endswith(".lc.gz") or n.endswith(".lc")]
        if not lc_names:
            return []
        chosen = next((n for n in lc_names if prefer_detector in n), lc_names[0])
        raw = z.read(chosen)
    return parse_light_curve(raw)


class FITSParser:
    """Thin class wrapper kept for import-site compatibility."""

    def parse_solexs_zip(self, zip_bytes: bytes) -> List[Dict[str, Any]]:
        return extract_light_curve_from_zip(zip_bytes, prefer_detector="SDD2")

    def parse_hel1os_zip(self, zip_bytes: bytes) -> List[Dict[str, Any]]:
        return extract_light_curve_from_zip(zip_bytes, prefer_detector="SDD2")
