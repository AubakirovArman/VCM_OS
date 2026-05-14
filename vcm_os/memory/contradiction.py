from typing import List, Tuple

from vcm_os.schemas import MemoryObject, Validity
from vcm_os.storage.sqlite_store import SQLiteStore


class ContradictionDetector:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def detect(self, new_mem: MemoryObject) -> List[Tuple[MemoryObject, str, float]]:
        """
        Returns list of (existing_memory, relation_type, confidence)
        """
        contradictions = []
        if new_mem.memory_type not in ("decision", "fact", "requirement"):
            return contradictions

        candidates = self.store.get_memories(
            project_id=new_mem.project_id,
            memory_type=new_mem.memory_type.value,
            limit=50,
        )
        for cand in candidates:
            if cand.memory_id == new_mem.memory_id:
                continue
            conf = self._check_contradiction(new_mem, cand)
            if conf > 0.5:
                contradictions.append((cand, "contradiction", conf))
        return contradictions

    def _check_contradiction(self, a: MemoryObject, b: MemoryObject) -> float:
        # Naive: compare key text fields
        texts_a = [a.raw_text or "", a.compressed_summary or "", a.semantic_summary or ""]
        texts_b = [b.raw_text or "", b.compressed_summary or "", b.semantic_summary or ""]
        best_sim = 0.0
        for ta in texts_a:
            for tb in texts_b:
                if not ta or not tb:
                    continue
                sim = self._text_overlap(ta, tb)
                if sim > best_sim:
                    best_sim = sim
        # High overlap but different decisions = likely contradiction
        if best_sim > 0.3 and a.validity == Validity.ACTIVE and b.validity == Validity.ACTIVE:
            return min(1.0, best_sim + 0.2)
        return 0.0

    def _text_overlap(self, a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        inter = len(words_a & words_b)
        union = len(words_a | words_b)
        return inter / union if union > 0 else 0.0
