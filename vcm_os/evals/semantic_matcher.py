"""Semantic goal matcher using embeddings (v0.9).

Replaces strict substring matching with cosine similarity between
embedded expected goals and embedded pack text.
"""
from typing import Dict, List

import numpy as np

from vcm_os.schemas import ContextPack
from vcm_os.storage.vector_index import VectorIndex


class SemanticGoalMatcher:
    """Match goals semantically via embeddings instead of verbatim substring."""

    def __init__(self, vector_index: VectorIndex, threshold: float = 0.65):
        self.vector_index = vector_index
        self.threshold = threshold

    def _embed(self, text: str) -> np.ndarray:
        """Embed text using the vector index model."""
        return self.vector_index.encode([text])[0]

    def match_goals(
        self,
        pack: ContextPack,
        expected_goals: List[str],
    ) -> Dict[str, float]:
        """Return semantic recall for goals.

        For each expected goal, embed it and compare against embedded pack text.
        If max similarity > threshold, count as hit.
        """
        if not expected_goals:
            return {"semantic_goal_recall": 1.0, "per_goal_scores": {}}

        # Embed pack text (chunked by sections)
        pack_chunks = []
        for sec in pack.sections:
            if sec.content.strip():
                pack_chunks.append(sec.content)
        if not pack_chunks:
            return {"semantic_goal_recall": 0.0, "per_goal_scores": {g: 0.0 for g in expected_goals}}

        try:
            goal_embeddings = [self._embed(g) for g in expected_goals]
            chunk_embeddings = [self._embed(c) for c in pack_chunks]
        except Exception:
            # Fallback: if embedding fails, return 0
            return {"semantic_goal_recall": 0.0, "per_goal_scores": {g: 0.0 for g in expected_goals}}

        # Normalize
        def _norm(v):
            n = np.linalg.norm(v)
            return v / n if n > 0 else v

        goal_embeddings = [_norm(v) for v in goal_embeddings]
        chunk_embeddings = [_norm(v) for v in chunk_embeddings]

        hits = 0
        per_goal = {}
        for i, goal_emb in enumerate(goal_embeddings):
            max_sim = 0.0
            for chunk_emb in chunk_embeddings:
                sim = float(np.dot(goal_emb, chunk_emb))
                if sim > max_sim:
                    max_sim = sim
            per_goal[expected_goals[i]] = max_sim
            if max_sim >= self.threshold:
                hits += 1

        recall = hits / len(expected_goals)
        return {
            "semantic_goal_recall": recall,
            "per_goal_scores": per_goal,
        }

    def match_decisions(
        self,
        pack: ContextPack,
        expected_decisions: List[str],
    ) -> Dict[str, float]:
        """Semantic decision recall."""
        if not expected_decisions:
            return {"semantic_decision_recall": 1.0, "per_decision_scores": {}}

        pack_chunks = [s.content for s in pack.sections if s.content.strip()]
        if not pack_chunks:
            return {"semantic_decision_recall": 0.0, "per_decision_scores": {d: 0.0 for d in expected_decisions}}

        try:
            dec_embeddings = [self._embed(d) for d in expected_decisions]
            chunk_embeddings = [self._embed(c) for c in pack_chunks]
        except Exception:
            return {"semantic_decision_recall": 0.0, "per_decision_scores": {d: 0.0 for d in expected_decisions}}

        def _norm(v):
            n = np.linalg.norm(v)
            return v / n if n > 0 else v

        dec_embeddings = [_norm(v) for v in dec_embeddings]
        chunk_embeddings = [_norm(v) for v in chunk_embeddings]

        hits = 0
        per_dec = {}
        for i, dec_emb in enumerate(dec_embeddings):
            max_sim = 0.0
            for chunk_emb in chunk_embeddings:
                sim = float(np.dot(dec_emb, chunk_emb))
                if sim > max_sim:
                    max_sim = sim
            per_dec[expected_decisions[i]] = max_sim
            if max_sim >= self.threshold:
                hits += 1

        recall = hits / len(expected_decisions)
        return {
            "semantic_decision_recall": recall,
            "per_decision_scores": per_dec,
        }
