from datetime import datetime, timezone
from typing import Optional

from vcm_os.schemas import SessionCheckpoint, SessionState
from vcm_os.storage.sqlite_store import SQLiteStore


class CheckpointManager:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def save_checkpoint(self, session_id: str, project_id: str, state: SessionState,
                        packed_summary: Optional[str] = None) -> SessionCheckpoint:
        cp = SessionCheckpoint(
            session_id=session_id,
            project_id=project_id,
            state=state,
            packed_summary=packed_summary,
        )
        self.store.insert_checkpoint(cp)
        # Update state with checkpoint ref
        state.last_checkpoint_id = cp.checkpoint_id
        self.store.upsert_session_state(state)
        return cp

    def load_latest_checkpoint(self, session_id: str) -> Optional[SessionCheckpoint]:
        return self.store.get_latest_checkpoint(session_id)
