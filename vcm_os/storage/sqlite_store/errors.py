import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from vcm_os.config import DB_PATH
from vcm_os.schemas import (
    DecisionEntry,
    EntityRef,
    ErrorEntry,
    EventRecord,
    MemoryObject,
    SessionCheckpoint,
    SessionIdentity,
    SessionState,
    SourcePointer,
)




class ErrorStoreMixin:

    def insert_error(self, entry: ErrorEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO errors (error_id, project_id, session_id, timestamp, error_text, error_kind, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry.error_id, entry.project_id, entry.session_id, entry.timestamp.isoformat(),
                 entry.error_text, entry.error_kind, entry.status),
            )

    def get_errors(self, project_id: str, limit: int = 100) -> List[ErrorEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM errors WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [
            ErrorEntry(
                error_id=r["error_id"],
                project_id=r["project_id"],
                session_id=r["session_id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                error_text=r["error_text"],
                error_kind=r["error_kind"],
                status=r["status"],
            )
            for r in rows
        ]