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




class EventStoreMixin:

    def insert_event(self, event: EventRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO events (event_id, session_id, project_id, timestamp, event_type, payload, raw_text) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.session_id,
                    event.project_id,
                    event.timestamp.isoformat(),
                    event.event_type,
                    json.dumps(event.payload),
                    event.raw_text,
                ),
            )

    def get_events(self, project_id: Optional[str] = None, session_id: Optional[str] = None, limit: int = 1000) -> List[EventRecord]:
        query = "SELECT * FROM events WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row: sqlite3.Row) -> EventRecord:
        return EventRecord(
            event_id=row["event_id"],
            session_id=row["session_id"],
            project_id=row["project_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event_type=row["event_type"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            raw_text=row["raw_text"],
        )