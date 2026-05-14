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




class StaleMarkerMixin:

    def insert_stale_marker(self, memory_id: str, reason: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stale_markers (memory_id, reason, marked_at) VALUES (?, ?, ?)",
                (memory_id, reason, datetime.now(timezone.utc).isoformat()),
            )

    def get_stale_markers(self, memory_ids: List[str]) -> List[str]:
        if not memory_ids:
            return []
        placeholders = ",".join("?" * len(memory_ids))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT memory_id FROM stale_markers WHERE memory_id IN ({placeholders})", memory_ids
            ).fetchall()
        return [r[0] for r in rows]