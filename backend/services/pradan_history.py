"""
Full-mission historical file catalogue from PRADAN, using its PrimeFaces
lazy-loaded data table pagination (confirmed empirically: the table accepts
up to 100 rows per page even though the UI default is 10, so an instrument's
entire multi-year catalogue can be pulled in a handful of requests instead
of one per day).

This is a real, working reverse-engineering of PRADAN's actual AJAX protocol:
  POST /al1/protected/browse.xhtml?id=<payload>
  javax.faces.partial.ajax=true
  javax.faces.source=tableForm:lazyDocTable
  tableForm:lazyDocTable_pagination=true
  tableForm:lazyDocTable_first=<offset>
  tableForm:lazyDocTable_rows=100
  javax.faces.ViewState=<token from the initial GET>
The response is a JSF partial-response XML with the updated table HTML
inside a CDATA block, which we extract and parse the same way as the
first-page HTML.

Paced with a short delay between pages — this is a real government portal,
not something to hammer with concurrent/rapid requests.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BROWSE_URL = "https://pradan1.issdc.gov.in/al1/protected/browse.xhtml"
PAGE_SIZE = 100
PAGE_DELAY_SECONDS = 2.5

# Day/half-day cadence instruments (SoLEXS, HEL1OS) genuinely only have a few
# thousand files across the whole mission, so a full backfill is reasonable.
# Imaging/high-cadence instruments (VELC, SUIT, SWIS, STEPS) produce orders of
# magnitude more files (VELC alone exceeded 20,000 and was still going) —
# exhaustively paging through years of those would mean tens of thousands of
# requests against a live government server, which isn't responsible use.
# Cap those at the most recent N files instead, disclosed honestly rather
# than silently truncated.
MAX_PAGES_FULL = 40  # ~4000 files — plenty for SoLEXS/HEL1OS's actual mission totals
MAX_PAGES_RECENT_ONLY = 15  # ~1500 most-recent files for high-cadence instruments
HIGH_CADENCE_INSTRUMENTS = {"velc", "suit", "swis", "steps"}

_ISO_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_SIZE_RE = re.compile(r"^\d+\.\d+$")
_VIEWSTATE_RE = re.compile(r'javax\.faces\.ViewState[^>]*value="([^"]+)"')
_UPDATE_RE = re.compile(r'<update id="tableForm:lazyDocTable"><!\[CDATA\[(.*?)\]\]></update>', re.DOTALL)


def _parse_rows(html_fragment: str, instrument: str) -> List[Dict[str, Any]]:
    # BeautifulSoup's html.parser drops orphaned <tbody> tags when a fragment
    # has no enclosing <table> (which this CDATA-extracted fragment doesn't) —
    # but the <tr> rows themselves still parse fine, and the update-id
    # targeting already guarantees this fragment is exclusively this table's
    # rows, so searching for all <tr> directly is safe here.
    soup = BeautifulSoup(html_fragment, "html.parser")

    files = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        download_link = None
        for cell in cells:
            a = cell.find("a", href=True)
            if not a or "/downloadData/" not in a["href"]:
                continue
            path = a["href"].lower().split("?")[0]
            # Different instruments package data differently — SoLEXS/HEL1OS
            # ship day-level .zip archives, VELC/SUIT ship raw .fits files
            # directly. Exclude .webp/.png preview-thumbnail links which also
            # live under /downloadData/ but aren't the actual data product.
            if path.endswith((".zip", ".fits", ".fit")):
                download_link = a
                break
        if not download_link:
            continue

        times = [c.get_text(strip=True) for c in cells if _ISO_TIME_RE.match(c.get_text(strip=True))]
        sizes = [c.get_text(strip=True) for c in cells if _SIZE_RE.match(c.get_text(strip=True))]
        href = download_link["href"]

        files.append(
            {
                "url": href if href.startswith("http") else f"https://pradan1.issdc.gov.in{href}",
                "filename": download_link.get_text(strip=True),
                "instrument": instrument,
                "start_time": times[0] if times else None,
                "end_time": times[1] if len(times) > 1 else None,
                "size_kb": sizes[0] if sizes else None,
            }
        )
    return files


def fetch_full_history(session: requests.Session, payload_name: str) -> List[Dict[str, Any]]:
    """Fetches pages of the given payload's data-product table, most recent
    first. Returns whatever was gathered so far on any failure (auth expired,
    connection reset, page structure changed, etc.) rather than raising or
    discarding partial progress — a mid-backfill network blip shouldn't lose
    everything already fetched."""
    payload_id = payload_name.lower()
    url = f"{BROWSE_URL}?id={payload_id}"
    max_pages = MAX_PAGES_RECENT_ONLY if payload_id in HIGH_CADENCE_INSTRUMENTS else MAX_PAGES_FULL

    try:
        initial = session.get(url, timeout=30)
        initial.raise_for_status()
    except requests.RequestException as exc:
        logger.error("PRADAN history fetch failed for %s (initial GET): %s", payload_name, exc)
        return []

    viewstate_match = _VIEWSTATE_RE.search(initial.text)
    if not viewstate_match:
        logger.error("PRADAN history fetch: no ViewState found for %s — page structure may have changed", payload_name)
        return []
    viewstate = viewstate_match.group(1)

    all_files: List[Dict[str, Any]] = []
    seen_urls = set()
    first = 0
    headers = {"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest"}

    for page_num in range(max_pages):
        form_data = {
            "tableForm": "tableForm",
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "tableForm:lazyDocTable",
            "javax.faces.partial.execute": "tableForm:lazyDocTable",
            "javax.faces.partial.render": "tableForm:lazyDocTable",
            "tableForm:lazyDocTable": "tableForm:lazyDocTable",
            "tableForm:lazyDocTable_pagination": "true",
            "tableForm:lazyDocTable_first": str(first),
            "tableForm:lazyDocTable_rows": str(PAGE_SIZE),
            "tableForm:lazyDocTable_skipChildren": "true",
            "tableForm:lazyDocTable_encodeFeature": "true",
            "javax.faces.ViewState": viewstate,
        }

        resp = None
        for attempt in range(3):
            try:
                resp = session.post(url, data=form_data, headers=headers, timeout=30)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                wait = PAGE_DELAY_SECONDS * (2 ** attempt)
                logger.warning("PRADAN history page %d for %s failed (attempt %d/3): %s — backing off %.1fs", page_num, payload_name, attempt + 1, exc, wait)
                time.sleep(wait)
        if resp is None:
            logger.error("PRADAN history page %d for %s failed after retries — keeping %d files gathered so far", page_num, payload_name, len(all_files))
            break

        match = _UPDATE_RE.search(resp.text)
        if not match:
            logger.warning("PRADAN history: no table update found on page %d for %s — stopping", page_num, payload_name)
            break

        rows = _parse_rows(match.group(1), payload_name)
        if not rows:
            break

        new_count = 0
        for row in rows:
            if row["url"] not in seen_urls:
                seen_urls.add(row["url"])
                all_files.append(row)
                new_count += 1

        logger.info("PRADAN history %s: page %d, %d rows (%d new)", payload_name, page_num, len(rows), new_count)

        if new_count == 0 or len(rows) < PAGE_SIZE:
            break  # last page reached

        first += PAGE_SIZE
        time.sleep(PAGE_DELAY_SECONDS)

    all_files.sort(key=lambda f: f.get("start_time") or "")
    return all_files


def summarize_history(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not files:
        return {"count": 0, "earliest": None, "latest": None, "by_month": {}}

    by_month: Dict[str, int] = {}
    for f in files:
        start = f.get("start_time") or ""
        month_key = start[:7] if len(start) >= 7 else "unknown"
        by_month[month_key] = by_month.get(month_key, 0) + 1

    return {
        "count": len(files),
        "earliest": files[0].get("start_time"),
        "latest": files[-1].get("start_time"),
        "by_month": dict(sorted(by_month.items())),
    }
