from datetime import datetime, timezone, timedelta
from typing import Dict, List

from vcm_os.schemas import MemoryObject, Validity
from vcm_os.storage.sqlite_store import SQLiteStore


class DecayEngine:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def run_decay(self, project_id: str) -> Dict[str, int]:
        stats = {"archived": 0, "compressed": 0, "unchanged": 0}
        objects = self.store.get_memories(project_id=project_id, limit=10000)
        now = datetime.now(timezone.utc)

        for obj in objects:
            if obj.never_delete:
                continue

            age_days = (now - obj.timestamp).days
            decay = self._compute_decay(obj, age_days)

            if obj.validity == Validity.SUPERSEDED:
                if age_days > 30 and getattr(obj, "access_count", 0) == 0:
                    obj.validity = Validity.ARCHIVED
                    self.store.update_memory(obj)
                    stats["archived"] += 1

            elif obj.memory_type.value == "event":
                if age_days > 7:
                    obj.validity = Validity.ARCHIVED
                    self.store.update_memory(obj)
                    stats["archived"] += 1

            elif obj.importance_score < 0.3 and age_days > 14:
                obj.validity = Validity.ARCHIVED
                self.store.update_memory(obj)
                stats["archived"] += 1

            else:
                stats["unchanged"] += 1

        return stats

    def _compute_decay(self, obj: MemoryObject, age_days: int) -> float:
        halflife = {
            "decision": 90,
            "error": 60,
            "requirement": 120,
            "fact": 30,
            "intent": 14,
            "code_change": 45,
            "procedure": 180,
            "reflection": 90,
            "uncertainty": 7,
            "preference": 365,
            "task": 30,
            "checkpoint": 30,
            "event": 3,
        }.get(obj.memory_type.value, 30)

        decay_factor = 0.5 ** (age_days / halflife)
        return decay_factor

    def update_access(self, memory_id: str) -> None:
        mem = self.store.get_memory(memory_id)
        if mem:
            mem.recency_score = 1.0
            mem.access_count = getattr(mem, "access_count", 0) + 1
            self.store.update_memory(mem)
