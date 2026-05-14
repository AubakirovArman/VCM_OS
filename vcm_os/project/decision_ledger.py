from typing import List, Optional

from vcm_os.schemas import MemoryObject, Validity
from vcm_os.storage.sqlite_store import SQLiteStore


class DecisionLedger:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def get_active_decisions(self, project_id: str, session_id: Optional[str] = None) -> List[MemoryObject]:
        return self.store.get_memories(
            project_id=project_id,
            session_id=session_id,
            memory_type="decision",
            validity="active",
            limit=100,
        )

    def get_proposed_decisions(self, project_id: str) -> List[MemoryObject]:
        return self.store.get_memories(
            project_id=project_id,
            memory_type="decision",
            validity="proposed",
            limit=50,
        )

    def supersede_decision(self, old_decision_id: str, new_decision_id: str) -> None:
        old = self.store.get_memory(old_decision_id)
        if old:
            old.validity = Validity.SUPERSEDED
            old.child_memory_ids.append(new_decision_id)
            self.store.update_memory(old)
        new = self.store.get_memory(new_decision_id)
        if new:
            new.parent_memory_id = old_decision_id
            self.store.update_memory(new)

    def reject_decision(self, decision_id: str) -> None:
        mem = self.store.get_memory(decision_id)
        if mem:
            mem.validity = Validity.REJECTED
            self.store.update_memory(mem)

    def confirm_decision(self, decision_id: str) -> None:
        mem = self.store.get_memory(decision_id)
        if mem and mem.validity == Validity.PROPOSED:
            mem.validity = Validity.ACTIVE
            self.store.update_memory(mem)
