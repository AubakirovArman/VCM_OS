from datetime import datetime, timezone
from typing import List, Optional

from vcm_os.schemas import SessionIdentity, SessionState, SessionStatus
from vcm_os.storage.sqlite_store import SQLiteStore


class SessionStore:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def create_session(self, project_id: str, title: Optional[str] = None, branch: Optional[str] = None) -> SessionIdentity:
        sess = SessionIdentity(project_id=project_id, title=title, branch=branch)
        self.store.upsert_session(sess)
        # Initialize empty state
        state = SessionState(session_id=sess.session_id)
        self.store.upsert_session_state(state)
        return sess

    def get_session(self, session_id: str) -> Optional[SessionIdentity]:
        return self.store.get_session(session_id)

    def list_sessions(self, project_id: Optional[str] = None, status: Optional[SessionStatus] = None) -> List[SessionIdentity]:
        return self.store.get_sessions(project_id=project_id, status=status.value if status else None)

    def update_session_state(self, state: SessionState) -> None:
        self.store.upsert_session_state(state)

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        return self.store.get_session_state(session_id)

    def pause_session(self, session_id: str) -> None:
        sess = self.store.get_session(session_id)
        if sess:
            sess.status = SessionStatus.PAUSED
            sess.last_active_at = datetime.now(timezone.utc)
            self.store.upsert_session(sess)

    def activate_session(self, session_id: str) -> None:
        sess = self.store.get_session(session_id)
        if sess:
            sess.status = SessionStatus.ACTIVE
            sess.last_active_at = datetime.now(timezone.utc)
            self.store.upsert_session(sess)
