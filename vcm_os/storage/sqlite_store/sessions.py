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




class SessionStoreMixin:

    def upsert_session(self, sess: SessionIdentity) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, project_id, title, created_at, last_active_at, status, "
                "branch, workspace_root, active_goal_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET last_active_at=excluded.last_active_at, status=excluded.status, "
                "title=excluded.title, branch=excluded.branch, workspace_root=excluded.workspace_root, "
                "active_goal_ids=excluded.active_goal_ids",
                (
                    sess.session_id, sess.project_id, sess.title,
                    sess.created_at.isoformat(), sess.last_active_at.isoformat(),
                    sess.status.value if hasattr(sess.status, 'value') else str(sess.status),
                    sess.branch, sess.workspace_root,
                    json.dumps(sess.active_goal_ids),
                ),
            )

    def get_session(self, session_id: str) -> Optional[SessionIdentity]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return SessionIdentity(
            session_id=row["session_id"],
            project_id=row["project_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_active_at=datetime.fromisoformat(row["last_active_at"]),
            status=row["status"],
            branch=row["branch"],
            workspace_root=row["workspace_root"],
            active_goal_ids=json.loads(row["active_goal_ids"]) if row["active_goal_ids"] else [],
        )

    def get_sessions(self, project_id: Optional[str] = None, status: Optional[str] = None) -> List[SessionIdentity]:
        query = "SELECT * FROM sessions WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY last_active_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            SessionIdentity(
                session_id=r["session_id"],
                project_id=r["project_id"],
                title=r["title"],
                created_at=datetime.fromisoformat(r["created_at"]),
                last_active_at=datetime.fromisoformat(r["last_active_at"]),
                status=r["status"],
                branch=r["branch"],
                workspace_root=r["workspace_root"],
                active_goal_ids=json.loads(r["active_goal_ids"]) if r["active_goal_ids"] else [],
            )
            for r in rows
        ]