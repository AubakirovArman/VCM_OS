from datetime import datetime, timezone
from typing import List, Optional

from vcm_os.llm_client import LLMClient
from vcm_os.schemas import MemoryObject, MemoryType
from vcm_os.storage.sqlite_store import SQLiteStore


class ReflectionEngine:
    def __init__(self, store: SQLiteStore, llm: LLMClient):
        self.store = store
        self.llm = llm

    async def maybe_reflect(
        self,
        project_id: str,
        trigger: str,
        min_evidence: int = 3,
    ) -> Optional[MemoryObject]:
        if trigger not in ("session_end", "N_errors", "N_related_events", "major_decision"):
            return None

        evidence = self._gather_evidence(project_id, trigger)
        if len(evidence) < min_evidence:
            return None

        texts = []
        for mem in evidence:
            text = mem.compressed_summary or mem.raw_text or ""
            if text:
                texts.append(text)

        reflection_data = await self.llm.generate_reflection(texts)
        if not reflection_data:
            return None

        mem = MemoryObject(
            project_id=project_id,
            memory_type=MemoryType.REFLECTION,
            source_type="manual_note",
            raw_text=reflection_data.get("reflection_text", ""),
            compressed_summary=reflection_data.get("reflection_text", "")[:400],
            semantic_summary=reflection_data.get("reflection_text", "")[:400],
            lessons_learned=reflection_data.get("claims", []),
            confidence_score=reflection_data.get("confidence", 0.5),
            importance_score=0.7,
            stability="stable",
            validity="active",
        )
        self.store.insert_memory(mem)
        # Link to evidence
        for ev in evidence:
            self.store.insert_link(mem.memory_id, ev.memory_id, "based_on", confidence=0.8)
        return mem

    def _gather_evidence(self, project_id: str, trigger: str) -> List[MemoryObject]:
        if trigger == "session_end":
            return self.store.get_memories(project_id=project_id, limit=20)
        elif trigger == "N_errors":
            return self.store.get_memories(project_id=project_id, memory_type="error", limit=10)
        elif trigger == "major_decision":
            return self.store.get_memories(project_id=project_id, memory_type="decision", limit=10)
        else:
            return self.store.get_memories(project_id=project_id, limit=15)
