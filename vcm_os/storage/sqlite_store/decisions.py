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




class DecisionStoreMixin:

    def insert_decision(self, entry: DecisionEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO decisions (decision_id, project_id, session_id, timestamp, decision_text, status, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry.decision_id, entry.project_id, entry.session_id, entry.timestamp.isoformat(),
                 entry.decision_text, entry.status, entry.confidence),
            )

    def get_decisions(self, project_id: str, limit: int = 100) -> List[DecisionEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [
            DecisionEntry(
                decision_id=r["decision_id"],
                project_id=r["project_id"],
                session_id=r["session_id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                decision_text=r["decision_text"],
                status=r["status"],
                confidence=r["confidence"],
            )
            for r in rows
        ]