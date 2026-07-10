"""
Durable, append-only prediction log — every forecast/watch/arrival estimate
this app makes gets written here with a timestamp, and later reconciled
against what actually happened. This is what "prediction accuracy" means in
practice: a real computed hit-rate from stored history, not an assumed number.

Backed by a Supabase Postgres table (see backend/supabase/schema.sql) rather
than local files, since local disk doesn't survive on serverless deploys
(e.g. Vercel). Category-specific prediction fields live in the `data` jsonb
column; `dedup_key` is unique per category so re-running the same cron cycle
never spams duplicate rows.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

TABLE = "predictions"

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — see backend/.env.example"
            )
        _client = create_client(url, key)
    return _client


def _flatten(row: Dict[str, Any]) -> Dict[str, Any]:
    """Merges a Supabase row back into the flat dict shape the rest of the
    codebase expects (data fields + dedup_key/recorded_at/verified/... at the
    top level), matching the old JSONL entry shape."""
    entry = dict(row.get("data") or {})
    entry["dedup_key"] = row["dedup_key"]
    entry["recorded_at"] = row["recorded_at"]
    entry["verified"] = row["verified"]
    if row.get("verified_at"):
        entry["verified_at"] = row["verified_at"]
    if row.get("correct") is not None:
        entry["correct"] = row["correct"]
    return entry


def record(category: str, entry: Dict[str, Any], dedup_key: str) -> bool:
    """Inserts entry unless one with the same dedup_key already exists —
    dedup_key should be a natural key for the real-world event/target being
    predicted (e.g. product_id+day), not a timestamp, so re-running the same
    cron cycle doesn't spam duplicate rows."""
    client = _get_client()
    existing = (
        client.table(TABLE)
        .select("id")
        .eq("category", category)
        .eq("dedup_key", dedup_key)
        .limit(1)
        .execute()
    )
    if existing.data:
        return False
    client.table(TABLE).insert(
        {
            "category": category,
            "dedup_key": dedup_key,
            "data": entry,
            "verified": False,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    return True


def _select(category: str, verified: Optional[bool] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    query = client.table(TABLE).select("*").eq("category", category)
    if verified is not None:
        query = query.eq("verified", verified)
    return query.execute().data or []


def list_unverified(category: str) -> List[Dict[str, Any]]:
    return [_flatten(row) for row in _select(category, verified=False)]


def mark_verified(category: str, dedup_key: str, updates: Dict[str, Any]) -> None:
    client = _get_client()
    existing = (
        client.table(TABLE)
        .select("data")
        .eq("category", category)
        .eq("dedup_key", dedup_key)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return
    merged_data = dict(existing.data[0].get("data") or {})
    merged_data.update(updates)
    client.table(TABLE).update(
        {
            "data": merged_data,
            "verified": True,
            "correct": updates.get("correct"),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("category", category).eq("dedup_key", dedup_key).execute()


def get_accuracy_summary(category: str) -> Dict[str, Any]:
    entries = [_flatten(row) for row in _select(category)]
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
