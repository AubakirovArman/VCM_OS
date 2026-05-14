"""Pack sufficiency verifier — checks if a context pack is sufficient to answer a query."""
import re
from typing import Dict, List, Set

from vcm_os.schemas import ContextPack, MemoryObject


class PackSufficiencyVerifier:
    """Verify that a context pack contains enough information to answer a query."""

    # Query-type → required memory types
    QUERY_TYPE_REQUIREMENTS = {
        "decision": ["decision"],
        "error": ["error"],
        "bug": ["error"],
        "state": ["fact", "decision", "code_change"],
        "status": ["fact", "decision", "code_change"],
        "goal": ["requirement", "decision"],
        "task": ["task", "decision"],
        "file": ["code_change", "fact"],
        "code": ["code_change", "fact"],
        "test": ["fact", "error"],
        "deploy": ["fact", "decision"],
        "security": ["error", "fact"],
    }

    def verify(self, query: str, pack: ContextPack, memories: List[MemoryObject]) -> Dict:
        """Return sufficiency score and gaps."""
        query_lower = query.lower()
        pack_text = " ".join(sec.content.lower() for sec in pack.sections)

        issues = []
        score = 1.0

        # 1. Query keyword coverage
        keywords = self._extract_keywords(query)
        uncovered = [kw for kw in keywords if kw not in pack_text]
        if uncovered:
            issues.append({"type": "keyword_gap", "missing": uncovered[:5]})
            score -= min(0.3, len(uncovered) * 0.05)

        # 2. Memory type requirements
        required_types = self._detect_required_types(query_lower)
        present_types = set()
        for m in memories:
            present_types.add(m.memory_type.value if hasattr(m.memory_type, "value") else str(m.memory_type))
        for req in required_types:
            if req not in present_types:
                issues.append({"type": "missing_memory_type", "required": req})
                score -= 0.15

        # 3. Pack diversity — not all from same source
        source_types = set()
        for m in memories:
            source_types.add(m.source_type.value if hasattr(m.source_type, "value") else str(m.source_type))
        if len(source_types) < 2 and len(memories) > 3:
            issues.append({"type": "low_diversity", "sources": list(source_types)})
            score -= 0.1

        # 4. Internal contradiction
        contradictions = self._detect_contradictions(pack_text, memories)
        if contradictions:
            issues.append({"type": "internal_contradiction", "details": contradictions[:3]})
            score -= 0.2

        # 5. Pack too short
        if len(pack_text) < 100:
            issues.append({"type": "pack_too_short", "length": len(pack_text)})
            score -= 0.3

        # 6. No citations in pack (pack should reference memory IDs)
        if not re.search(r"mem_[a-z0-9]+", pack_text):
            issues.append({"type": "no_citations_in_pack"})
            score -= 0.05

        return {
            "sufficient": score >= 0.7 and len([i for i in issues if i["type"] in ("missing_memory_type", "internal_contradiction")]) == 0,
            "score": max(0.0, round(score, 2)),
            "issues": issues,
        }

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query."""
        words = re.findall(r"\b[a-z]{4,}\b", query.lower())
        stopwords = {"what", "where", "when", "how", "why", "which", "who", "is", "are", "the", "a", "an", "this", "that", "current", "project", "about", "for", "with", "from", "does", "did", "do", "can", "should", "would", "could", "will", "have", "has", "had", "been", "being", "was", "were", "and", "but", "or", "not", "yes", "no"}
        return [w for w in words if w not in stopwords]

    def _detect_required_types(self, query_lower: str) -> List[str]:
        """Detect what memory types the query likely needs."""
        required = []
        for keyword, types in self.QUERY_TYPE_REQUIREMENTS.items():
            if keyword in query_lower:
                required.extend(types)
        return list(dict.fromkeys(required))

    def _detect_contradictions(self, pack_text: str, memories: List[MemoryObject]) -> List[Dict]:
        """Detect simple contradictions within the pack."""
        contradictions = []
        # Check for active vs rejected decisions in same pack
        active_decisions = []
        rejected_decisions = []
        for m in memories:
            if m.memory_type == "decision" and m.decisions:
                for d in m.decisions:
                    stmt = d.statement.lower()
                    if d.status.value == "active":
                        active_decisions.append(stmt)
                    elif d.status.value == "rejected":
                        rejected_decisions.append(stmt)
        for active in active_decisions:
            for rejected in rejected_decisions:
                # Simple overlap check
                if len(active) > 10 and len(rejected) > 10:
                    # If they share significant words but one is active and one rejected
                    active_words = set(active.split())
                    rejected_words = set(rejected.split())
                    overlap = active_words & rejected_words
                    if len(overlap) >= 3:
                        contradictions.append({
                            "type": "decision_conflict",
                            "active": active[:60],
                            "rejected": rejected[:60],
                        })
        # Check for pass/fail contradictions
        has_pass = "passed" in pack_text and "test" in pack_text
        has_fail = "failed" in pack_text and "test" in pack_text
        if has_pass and has_fail:
            # Only contradiction if they're about the same test suite without context
            if pack_text.count("test") < 3:
                contradictions.append({"type": "test_status_conflict", "detail": "both pass and fail mentioned"})
        return contradictions
