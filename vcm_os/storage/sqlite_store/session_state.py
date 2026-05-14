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




class SessionStateMixin:

    def upsert_session_state(self, state: SessionState) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO session_states (session_id, active_goals, active_files, current_plan, open_tasks, "
                "recent_decisions, recent_errors, current_code_branch, tool_state, unresolved_assumptions, "
                "last_checkpoint_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET active_goals=excluded.active_goals, "
                "active_files=excluded.active_files, current_plan=excluded.current_plan, "
                "open_tasks=excluded.open_tasks, recent_decisions=excluded.recent_decisions, "
                "recent_errors=excluded.recent_errors, current_code_branch=excluded.current_code_branch, "
                "tool_state=excluded.tool_state, unresolved_assumptions=excluded.unresolved_assumptions, "
                "last_checkpoint_id=excluded.last_checkpoint_id",
                (
                    state.session_id,
                    json.dumps(state.active_goals),
                    json.dumps(state.active_files),
                    state.current_plan,
                    json.dumps(state.open_tasks),
                    json.dumps(state.recent_decisions),
                    json.dumps(state.recent_errors),
                    state.current_code_branch,
                    json.dumps(state.tool_state) if state.tool_state else None,
                    json.dumps(state.unresolved_assumptions),
                    state.last_checkpoint_id,
                ),
            )

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM session_states WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return None
        def _load(val):
            return json.loads(val) if val else []
        return SessionState(
            session_id=row["session_id"],
            active_goals=_load(row["active_goals"]),
            active_files=_load(row["active_files"]),
            current_plan=row["current_plan"],
            open_tasks=_load(row["open_tasks"]),
            recent_decisions=_load(row["recent_decisions"]),
            recent_errors=_load(row["recent_errors"]),
            current_code_branch=row["current_code_branch"],
            tool_state=json.loads(row["tool_state"]) if row["tool_state"] else None,
            unresolved_assumptions=_load(row["unresolved_assumptions"]),
            last_checkpoint_id=row["last_checkpoint_id"],
        )