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




class CanonicalHashMixin:

    def get_canonical_hashes(self, project_id: str, session_id: Optional[str] = None) -> set:
        query = "SELECT project_id, session_id, memory_type, content_hash FROM canonical_hashes WHERE project_id = ?"
        params: List[Any] = [project_id]
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return set((r[0], r[1], r[2], r[3]) for r in rows)

    def add_canonical_hash(self, project_id: str, session_id: Optional[str], memory_type: str, content_hash: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO canonical_hashes (project_id, session_id, memory_type, content_hash) VALUES (?, ?, ?, ?)",
                (project_id, session_id, memory_type, content_hash),
            )