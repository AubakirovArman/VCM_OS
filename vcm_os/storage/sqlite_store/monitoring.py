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




class MonitoringMixin:

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_memories = conn.execute("SELECT COUNT(*) FROM memory_objects").fetchone()[0]
            type_counts = conn.execute("SELECT memory_type, COUNT(*) FROM memory_objects GROUP BY memory_type").fetchall()
            total_projects = conn.execute("SELECT COUNT(DISTINCT project_id) FROM events").fetchone()[0]
            total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM events WHERE session_id IS NOT NULL").fetchone()[0]
            stale_count = conn.execute("SELECT COUNT(*) FROM memory_objects WHERE validity = 'stale'").fetchone()[0]
            superseded_count = conn.execute("SELECT COUNT(*) FROM memory_objects WHERE validity = 'superseded'").fetchone()[0]
            db_size = conn.execute("PRAGMA page_count").fetchone()[0] * conn.execute("PRAGMA page_size").fetchone()[0]
        return {
            "events": total_events,
            "memories": total_memories,
            "memory_types": {r[0]: r[1] for r in type_counts},
            "projects": total_projects,
            "sessions": total_sessions,
            "stale_memories": stale_count,
            "superseded_memories": superseded_count,
            "db_size_bytes": db_size,
        }


    def apply_retention(self, max_age_days: int = 90, max_memories_per_project: int = 1000):
        with self._conn() as conn:
            old_events = conn.execute(
                "SELECT event_id FROM events WHERE timestamp < datetime('now', '-{} days')".format(max_age_days)
            ).fetchall()
            old_event_ids = [r[0] for r in old_events]
            if old_event_ids:
                placeholders = ",".join("?" * len(old_event_ids))
                conn.execute(f"DELETE FROM events WHERE event_id IN ({placeholders})", old_event_ids)

            projects = conn.execute("SELECT DISTINCT project_id FROM memory_objects").fetchall()
            for (pid,) in projects:
                overs = conn.execute(
                    "SELECT memory_id FROM memory_objects WHERE project_id = ? AND "
                    "(never_delete IS NULL OR never_delete = 0) "
                    "ORDER BY importance_score DESC, recency_score DESC LIMIT -1 OFFSET ?",
                    (pid, max_memories_per_project),
                ).fetchall()
                for (mid,) in overs:
                    conn.execute("DELETE FROM memory_links WHERE source_id = ? OR target_id = ?", (mid, mid))
                    conn.execute("DELETE FROM memory_objects WHERE memory_id = ?", (mid,))