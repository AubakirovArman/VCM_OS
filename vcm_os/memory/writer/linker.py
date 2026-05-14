from typing import List

from vcm_os.schemas import MemoryObject, MemoryType, Validity


class LinkerMixin:
    def _link_to_existing(self, obj: MemoryObject) -> List[str]:
        linked = []
        if obj.file_references:
            existing = self.store.get_memories(project_id=obj.project_id, limit=100)
            for ex in existing:
                if ex.memory_id == obj.memory_id:
                    continue
                shared_files = set(obj.file_references) & set(ex.file_references)
                if shared_files:
                    self.store.insert_link(obj.memory_id, ex.memory_id, "shared_file", confidence=0.8)
                    linked.append(ex.memory_id)
        return linked

    def _detect_contradictions(self, obj: MemoryObject) -> int:
        if obj.memory_type != MemoryType.DECISION or not obj.decisions:
            return 0
        count = 0
        existing = self.store.get_memories(project_id=obj.project_id, memory_type=MemoryType.DECISION.value, limit=50)
        for ex in existing:
            if ex.memory_id == obj.memory_id:
                continue
            if ex.validity != Validity.ACTIVE or obj.validity != Validity.ACTIVE:
                continue
            if not ex.decisions:
                continue
            obj_text = obj.decisions[0].statement.lower()
            ex_text = ex.decisions[0].statement.lower()
            if obj_text == ex_text:
                continue
            shared_files = set(obj.file_references or []) & set(ex.file_references or [])
            obj_words = set(obj_text.split())
            ex_words = set(ex_text.split())
            shared_words = obj_words & ex_words
            if shared_files or len(shared_words) >= 2:
                if obj.timestamp > ex.timestamp:
                    ex.validity = Validity.SUPERSEDED
                    ex.contradiction_links.append(obj.memory_id)
                    self.store.update_memory(ex)
                    count += 1
                elif ex.timestamp > obj.timestamp:
                    obj.validity = Validity.SUPERSEDED
                    obj.contradiction_links.append(ex.memory_id)
                    count += 1
        return count
