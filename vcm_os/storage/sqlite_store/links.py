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




class LinkStoreMixin:

    def insert_link(self, source_id: str, target_id: str, relation_type: str, confidence: float = 1.0) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory_links (source_id, target_id, relation_type, confidence) VALUES (?, ?, ?, ?)",
                (source_id, target_id, relation_type, confidence),
            )

    def get_linked(self, memory_id: str, relation_type: Optional[str] = None) -> List[Tuple[str, str, float]]:
        query = "SELECT target_id, relation_type, confidence FROM memory_links WHERE source_id = ?"
        params: List[Any] = [memory_id]
        if relation_type:
            query += " AND relation_type = ?"
            params.append(relation_type)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [(r["target_id"], r["relation_type"], r["confidence"]) for r in rows]

    def get_reverse_linked(self, memory_id: str, relation_type: Optional[str] = None) -> List[Tuple[str, str, float]]:
        query = "SELECT source_id, relation_type, confidence FROM memory_links WHERE target_id = ?"
        params: List[Any] = [memory_id]
        if relation_type:
            query += " AND relation_type = ?"
            params.append(relation_type)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [(r["source_id"], r["relation_type"], r["confidence"]) for r in rows]