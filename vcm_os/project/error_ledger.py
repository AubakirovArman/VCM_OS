from typing import List, Optional

from vcm_os.schemas import MemoryObject
from vcm_os.storage.sqlite_store import SQLiteStore


class ErrorLedger:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def get_errors(self, project_id: str, session_id: Optional[str] = None, kind: Optional[str] = None) -> List[MemoryObject]:
        mems = self.store.get_memories(
            project_id=project_id,
            session_id=session_id,
            memory_type="error",
            limit=100,
        )
        if kind:
            mems = [m for m in mems if any(e.kind == kind for e in m.errors_found)]
        return mems

    def get_recent_errors(self, project_id: str, limit: int = 10) -> List[MemoryObject]:
        return self.store.get_memories(
            project_id=project_id,
            memory_type="error",
            limit=limit,
        )

    def add_verified_fix(self, error_memory_id: str, fix_text: str) -> None:
        mem = self.store.get_memory(error_memory_id)
        if not mem:
            return
        for err in mem.errors_found:
            if not err.verified_fix:
                err.verified_fix = fix_text
        mem.lessons_learned.append(f"Verified fix: {fix_text[:200]}")
        self.store.update_memory(mem)
