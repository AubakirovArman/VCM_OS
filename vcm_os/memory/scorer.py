from datetime import datetime, timezone
from typing import List, Tuple

from vcm_os.schemas import MemoryObject, MemoryRequest
from vcm_os.storage.vector_index import VectorIndex


class MemoryScorer:
    def __init__(self, vector_index: VectorIndex):
        self.vector_index = vector_index

    def rerank(
        self,
        candidates: List[MemoryObject],
        request: MemoryRequest,
    ) -> List[Tuple[MemoryObject, float]]:
        query = request.query
        # Encode query once
        qvec = self.vector_index.encode([query])[0] if candidates else None

        scored = []
        for mem in candidates:
            score = self._compute_score(mem, request, qvec)
            scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _compute_score(
        self,
        mem: MemoryObject,
        request: MemoryRequest,
        qvec,
    ) -> float:
        # Semantic relevance
        relevance = 0.0
        if mem.embedding_vector and qvec is not None:
            import numpy as np
            v = np.array(mem.embedding_vector)
            norm_v = np.linalg.norm(v)
            norm_q = np.linalg.norm(qvec)
            if norm_v > 0 and norm_q > 0:
                relevance = float(np.dot(v, qvec) / (norm_v * norm_q))
        else:
            # Fallback: simple text overlap
            query_words = set(request.query.lower().split())
            text = (mem.semantic_summary or mem.compressed_summary or mem.raw_text or "").lower()
            text_words = set(text.split())
            overlap = len(query_words & text_words)
            relevance = overlap / max(len(query_words), 1)

        # Components from plan priority formula
        importance = mem.importance_score
        recency = mem.recency_score
        canonicality = 1.0 if mem.stability == "canonical" else (0.7 if mem.stability == "stable" else 0.3)
        confidence = mem.confidence_score
        # Task affinity: boost decisions/errors for debugging
        task_affinity = 0.5
        if request.task_type == "debugging" and mem.memory_type in ("error", "decision"):
            task_affinity = 1.0
        # Staleness penalty
        staleness = 0.0
        if mem.validity == "superseded":
            staleness = 1.0
        contradiction_penalty = min(len(mem.contradiction_links) * 0.1, 0.5)

        score = (
            0.25 * relevance
            + 0.15 * importance
            + 0.10 * recency
            + 0.15 * canonicality
            + 0.10 * confidence
            + 0.10 * task_affinity
            + 0.10 * 0.5  # graph centrality stub
            - 0.10 * staleness
            - 0.10 * contradiction_penalty
        )
        return max(0.0, score)
