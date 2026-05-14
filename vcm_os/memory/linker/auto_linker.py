"""Auto-link memories during ingestion to reduce orphan ratio."""
import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from vcm_os.schemas import MemoryObject, MemoryType


class AutoLinker:
    """Create links between memories based on multiple signals."""

    # Memory type pairs that should be linked
    TYPE_RELATIONS = {
        ("decision", "task"): "decision_affects_task",
        ("decision", "code_change"): "decision_affects_file",
        ("error", "code_change"): "error_caused_by_symbol",
        ("error", "decision"): "error_led_to_decision",
        ("task", "goal"): "task_achieves_goal",
        ("goal", "decision"): "goal_requires_decision",
        ("tool_call", "error"): "tool_output_verifies_error",
        ("tool_call", "code_change"): "tool_output_verifies_fix",
        ("intent", "goal"): "intent_promoted_to_goal",
        ("fact", "decision"): "fact_supports_decision",
        ("requirement", "decision"): "requirement_leads_to_decision",
    }

    def __init__(self, store):
        self.store = store

    def link(self, obj: MemoryObject) -> List[Tuple[str, str, float]]:
        """Create links for a new memory object. Returns list of (target_id, relation, confidence)."""
        links = []
        existing = self.store.get_memories(project_id=obj.project_id, limit=100)

        for ex in existing:
            if ex.memory_id == obj.memory_id:
                continue

            # 1. Same session link
            if obj.session_id and ex.session_id and obj.session_id == ex.session_id:
                links.append((ex.memory_id, "same_session", 0.9))
                continue

            # 2. Type-based relation
            rel = self._type_relation(obj, ex)
            if rel:
                links.append((ex.memory_id, rel, 0.7))
                continue

            # 3. Shared file references
            shared_files = set(obj.file_references or []) & set(ex.file_references or [])
            if shared_files:
                links.append((ex.memory_id, "shared_file", 0.8))
                continue

            # 4. Keyword overlap
            overlap = self._keyword_overlap(obj, ex)
            if overlap >= 3:
                links.append((ex.memory_id, "keyword_overlap", min(0.5 + overlap * 0.05, 0.8)))
                continue

            # 5. Temporal proximity (within 5 minutes, same project)
            if self._temporal_proximity(obj, ex):
                links.append((ex.memory_id, "temporal_proximity", 0.5))

        # Store links in DB
        created = []
        for target_id, relation, confidence in links:
            self.store.insert_link(obj.memory_id, target_id, relation, confidence)
            created.append((target_id, relation, confidence))

        return created

    def _type_relation(self, obj: MemoryObject, ex: MemoryObject) -> str:
        """Check if memory types have a known relation."""
        t1 = obj.memory_type.value if hasattr(obj.memory_type, "value") else str(obj.memory_type)
        t2 = ex.memory_type.value if hasattr(ex.memory_type, "value") else str(ex.memory_type)
        # Check both directions
        for pair, rel in self.TYPE_RELATIONS.items():
            if (t1, t2) == pair or (t2, t1) == pair:
                return rel
        return ""

    def _keyword_overlap(self, obj: MemoryObject, ex: MemoryObject) -> int:
        """Count meaningful overlapping words between two memories."""
        obj_text = " ".join([obj.raw_text or "", obj.compressed_summary or "", obj.semantic_summary or ""])
        ex_text = " ".join([ex.raw_text or "", ex.compressed_summary or "", ex.semantic_summary or ""])
        obj_words = self._extract_keywords(obj_text)
        ex_words = self._extract_keywords(ex_text)
        return len(obj_words & ex_words)

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        stopwords = {
            "lorem", "ipsum", "dolor", "amet", "consectetur", "adipiscing", "elit",
            "this", "that", "with", "from", "have", "been", "were", "they", "their",
            "would", "could", "should", "there", "where", "when", "what", "how",
        }
        return set(w for w in words if w not in stopwords)

    def _temporal_proximity(self, obj: MemoryObject, ex: MemoryObject) -> bool:
        """Check if two memories are within 5 minutes."""
        if not obj.timestamp or not ex.timestamp:
            return False
        try:
            # Parse ISO timestamps
            t1 = datetime.fromisoformat(obj.timestamp.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(ex.timestamp.replace("Z", "+00:00"))
            diff = abs((t1 - t2).total_seconds())
            return diff < 300  # 5 minutes
        except Exception:
            return False
