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




class CheckpointStoreMixin:

    def insert_checkpoint(self, cp: SessionCheckpoint) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO checkpoints (checkpoint_id, session_id, project_id, timestamp, state, packed_summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    cp.checkpoint_id, cp.session_id, cp.project_id,
                    cp.timestamp.isoformat(), json.dumps(cp.state.model_dump()), cp.packed_summary,
                ),
            )

    def get_latest_checkpoint(self, session_id: str) -> Optional[SessionCheckpoint]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1", (session_id,)
            ).fetchone()
        if not row:
            return None
        return SessionCheckpoint(
            checkpoint_id=row["checkpoint_id"],
            session_id=row["session_id"],
            project_id=row["project_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            state=json.loads(row["state"]) if row["state"] else {},
            packed_summary=row["packed_summary"],
        )

    def get_checkpoints(self, session_id: str) -> List[SessionCheckpoint]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY timestamp DESC", (session_id,)
            ).fetchall()
        return [
            SessionCheckpoint(
                checkpoint_id=r["checkpoint_id"],
                session_id=r["session_id"],
                project_id=r["project_id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                state=json.loads(r["state"]) if r["state"] else {},
                packed_summary=r["packed_summary"],
            )
            for r in rows
        ]