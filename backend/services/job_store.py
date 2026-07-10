"""
Persistent store for cron job outputs (JSON snapshots on disk).
API reads pre-fetched data so requests never block on NOAA network calls.
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

DATA_DIR = Path(os.getenv("JOB_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "snapshots"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status_path = DATA_DIR / "job_status.json"
        if not self._status_path.exists():
            self._write_status({"jobs": {}, "updated_at": datetime.now(timezone.utc).isoformat()})

    def _path(self, key: str) -> Path:
        return DATA_DIR / f"{key}.json"

    def save(self, key: str, data: Any) -> None:
        payload = {
            "key": key,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        with self._lock:
            self._path(key).write_text(json.dumps(payload, default=str), encoding="utf-8")
        logger.debug("JobStore saved %s", key)

    def load(self, key: str, max_age_seconds: Optional[int] = None) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if max_age_seconds is not None:
                saved = datetime.fromisoformat(payload["saved_at"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - saved).total_seconds()
                if age > max_age_seconds:
                    return None
            return payload.get("data")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("JobStore load failed for %s: %s", key, exc)
            return None

    def meta(self, key: str) -> Optional[Dict[str, str]]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {"key": key, "saved_at": payload.get("saved_at")}
        except (json.JSONDecodeError, KeyError):
            return None

    def record_run(self, job_name: str, success: bool, detail: str = "", duration_ms: float = 0) -> None:
        with self._lock:
            status = self._read_status()
            status["jobs"][job_name] = {
                "last_run": datetime.now(timezone.utc).isoformat(),
                "success": success,
                "detail": detail,
                "duration_ms": round(duration_ms, 1),
            }
            status["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_status(status)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            status = self._read_status()
        snapshots: List[Dict[str, str]] = []
        for path in sorted(DATA_DIR.glob("*.json")):
            if path.name == "job_status.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                snapshots.append({"key": path.stem, "saved_at": payload.get("saved_at", "")})
            except json.JSONDecodeError:
                continue
        status["snapshots"] = snapshots
        status["data_dir"] = str(DATA_DIR)
        return status

    def _read_status(self) -> Dict[str, Any]:
        try:
            return json.loads(self._status_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            # A torn write (e.g. a second process writing this same file
            # concurrently — this JobStore's lock only protects within one
            # process) shouldn't crash every endpoint that reports job
            # status. Recover with an empty status rather than propagating.
            logger.warning("job_status.json unreadable (%s) — resetting", exc)
            empty = {"jobs": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
            self._write_status(empty)
            return empty

    def _write_status(self, data: Dict[str, Any]) -> None:
        self._status_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


job_store = JobStore()
