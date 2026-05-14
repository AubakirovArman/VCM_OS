"""Cross-project memory transfer — detect similar projects and warn about relevant decisions/errors."""
import re
from typing import Dict, List, Set, Tuple

from vcm_os.schemas import MemoryObject, MemoryType, Validity


class CrossProjectTransfer:
    """Detect similar projects and surface transferable memories as warnings."""

    def __init__(self, store):
        self.store = store

    def find_similar_projects(self, project_id: str, min_similarity: float = 0.3) -> List[Tuple[str, float]]:
        """Find projects similar to the given one. Returns list of (project_id, similarity_score)."""
        # Get keyword signatures for all projects
        signatures = self._project_signatures()
        if project_id not in signatures:
            return []

        target_sig = signatures[project_id]
        results = []

        for pid, sig in signatures.items():
            if pid == project_id:
                continue
            sim = self._jaccard_similarity(target_sig, sig)
            if sim >= min_similarity:
                results.append((pid, round(sim, 3)))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_transferable_memories(
        self,
        project_id: str,
        query: str = "",
        max_results: int = 5,
    ) -> List[Dict]:
        """Get decisions/errors from similar projects as warnings."""
        similar = self.find_similar_projects(project_id)
        if not similar:
            return []

        query_keywords = self._extract_keywords(query)
        warnings = []

        for sim_pid, sim_score in similar[:3]:
            # Get active decisions and errors from similar project
            mems = self.store.get_memories(project_id=sim_pid, limit=100)
            for m in mems:
                if m.memory_type not in (MemoryType.DECISION.value, MemoryType.ERROR.value):
                    continue
                if m.validity not in (Validity.ACTIVE.value, Validity.PROPOSED.value):
                    continue

                # Relevance: keyword overlap with query or target project
                mem_keywords = self._extract_keywords(
                    " ".join([m.raw_text or "", m.compressed_summary or ""])
                )
                overlap = len(query_keywords & mem_keywords) if query_keywords else 1

                if overlap > 0 or not query:
                    warnings.append({
                        "source_project": sim_pid,
                        "similarity": sim_score,
                        "memory_type": m.memory_type,
                        "summary": m.compressed_summary or m.raw_text or "",
                        "warning": f"Similar project {sim_pid} had this {m.memory_type}",
                        "relevance": overlap,
                    })

        # Sort by relevance and similarity
        warnings.sort(key=lambda x: (x["relevance"], x["similarity"]), reverse=True)
        return warnings[:max_results]

    def _project_signatures(self) -> Dict[str, Set[str]]:
        """Build keyword signature for each project."""
        signatures = {}
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT project_id, raw_text, compressed_summary, memory_type, file_references FROM memory_objects"
            ).fetchall()

        for row in rows:
            pid = row["project_id"]
            text = " ".join([row["raw_text"] or "", row["compressed_summary"] or ""])
            keywords = self._extract_keywords(text)
            # Add memory type as feature
            if row["memory_type"]:
                keywords.add(row["memory_type"].lower())
            # Add file extensions as features
            files = row["file_references"] or ""
            for ext in re.findall(r"\.([a-zA-Z0-9]+)", files):
                keywords.add(f"ext:{ext.lower()}")

            if pid not in signatures:
                signatures[pid] = set()
            signatures[pid].update(keywords)

        return signatures

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords."""
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        stopwords = {
            "this", "that", "with", "from", "have", "been", "were", "they", "their",
            "would", "could", "should", "there", "where", "when", "what", "how",
            "lorem", "ipsum", "dolor", "amet",
        }
        return set(w for w in words if w not in stopwords)

    def _jaccard_similarity(self, a: Set[str], b: Set[str]) -> float:
        """Compute Jaccard similarity between two sets."""
        if not a and not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0
