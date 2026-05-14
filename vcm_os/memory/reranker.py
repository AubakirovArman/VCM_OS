from typing import Dict, List, Tuple

from vcm_os.schemas import MemoryObject


def reciprocal_rank_fusion(
    results_lists: List[List[Tuple[str, float]]],
    k: float = 60.0,
) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}
    for rlist in results_lists:
        for rank, (doc_id, _) in enumerate(rlist):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores


class Reranker:
    def __init__(self):
        pass

    def rerank_rrf(
        self,
        vector_results: List[Tuple[str, float]],
        sparse_results: List[Tuple[str, float]],
        metadata_results: List[Tuple[str, float]],
        top_k: int = 50,
    ) -> List[Tuple[str, float]]:
        fused = reciprocal_rank_fusion([vector_results, sparse_results, metadata_results])
        return fused[:top_k]

    def rerank_by_recency_and_importance(
        self,
        memories: List[MemoryObject],
        base_scores: Dict[str, float],
        task_type: str = "general",
    ) -> List[Tuple[MemoryObject, float]]:
        scored = []
        for mem in memories:
            base = base_scores.get(mem.memory_id, 0.5)
            recency = mem.recency_score
            importance = mem.importance_score
            confidence = mem.confidence_score

            # Task-specific boost
            task_boost = 0.0
            if task_type == "debugging":
                if mem.memory_type == "error":
                    task_boost = 0.3
                elif mem.memory_type == "decision":
                    task_boost = 0.15
                elif mem.memory_type == "code_change":
                    task_boost = 0.1
            elif task_type == "architecture":
                if mem.memory_type == "decision":
                    task_boost = 0.3
                elif mem.memory_type == "requirement":
                    task_boost = 0.2
            elif task_type == "feature":
                if mem.memory_type == "code_change":
                    task_boost = 0.2
                elif mem.memory_type == "decision":
                    task_boost = 0.15

            # Penalize stale/superseded
            penalty = 0.0
            if mem.validity == "superseded":
                penalty = 0.5
            elif mem.validity == "rejected":
                penalty = 0.8

            # Boost canonical/stable memories
            stability_boost = 0.0
            if mem.stability == "canonical":
                stability_boost = 0.1
            elif mem.stability == "stable":
                stability_boost = 0.05

            score = (
                0.35 * base
                + 0.15 * recency
                + 0.20 * importance
                + 0.10 * confidence
                + task_boost
                + stability_boost
                - penalty
            )
            scored.append((mem, max(0.0, score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
