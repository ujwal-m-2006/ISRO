"""
Durable, append-only prediction log — every forecast/watch/arrival estimate
this app makes gets written here with a timestamp, and later reconciled
against what actually happened. This is what "prediction accuracy" means in
practice: a real computed hit-rate from stored history, not an assumed number.

One JSONL file per category under backend/data/predictions/. JSONL (not a
single JSON array) so appending never requires reading+rewriting the whole
file, and a torn write only corrupts one line, not the entire history.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("JOB_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "snapshots")).parent / "predictions"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


def _path(category: str) -> Path:
    return DATA_DIR / f"{category}.jsonl"


def _read_all(category: str) -> List[Dict[str, Any]]:
    path = _path(category)
    if not path.exists():
        return []
    entries = []
    with _lock:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # one torn line shouldn't lose the rest of the log
    return entries


def _write_all(category: str, entries: List[Dict[str, Any]]) -> None:
    path = _path(category)
    with _lock:
        path.write_text("\n".join(json.dumps(e, default=str) for e in entries) + "\n", encoding="utf-8")


def record(category: str, entry: Dict[str, Any], dedup_key: str) -> bool:
    """Appends entry unless one with the same dedup_key already exists —
    dedup_key should be a natural key for the real-world event/target being
    predicted (e.g. product_id+day), not a timestamp, so re-running the same
    cron cycle doesn't spam duplicate rows."""
    entries = _read_all(category)
    if any(e.get("dedup_key") == dedup_key for e in entries):
        return False
    entry = dict(entry)
    entry["dedup_key"] = dedup_key
    entry["recorded_at"] = datetime.now(timezone.utc).isoformat()
    entry["verified"] = False
    entries.append(entry)
    _write_all(category, entries)
    return True


def list_unverified(category: str) -> List[Dict[str, Any]]:
    return [e for e in _read_all(category) if not e.get("verified")]


def mark_verified(category: str, dedup_key: str, updates: Dict[str, Any]) -> None:
    entries = _read_all(category)
    changed = False
    for e in entries:
        if e.get("dedup_key") == dedup_key:
            e.update(updates)
            e["verified"] = True
            e["verified_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
    if changed:
        _write_all(category, entries)


def get_accuracy_summary(category: str) -> Dict[str, Any]:
    entries = _read_all(category)
    verified = [e for e in entries if e.get("verified")]
    correct = [e for e in verified if e.get("correct")]
    return {
        "category": category,
        "total_recorded": len(entries),
        "total_verified": len(verified),
        "total_pending": len(entries) - len(verified),
        "correct": len(correct),
        "accuracy_pct": round(len(correct) / len(verified) * 100, 1) if verified else None,
        "recent": sorted(entries, key=lambda e: e.get("recorded_at", ""), reverse=True)[:20],
    }
