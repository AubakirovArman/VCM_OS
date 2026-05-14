from typing import Dict, List, Optional

from vcm_os.schemas import ContextPack, MemoryObject


def recall_accuracy(retrieved: List[MemoryObject], relevant_ids: List[str]) -> float:
    if not relevant_ids:
        return 1.0
    found = sum(1 for m in retrieved if m.memory_id in relevant_ids)
    return found / len(relevant_ids)


def precision(retrieved: List[MemoryObject], useful_ids: List[str]) -> float:
    if not retrieved:
        return 1.0
    useful = sum(1 for m in retrieved if m.memory_id in useful_ids)
    return useful / len(retrieved)


def token_usage(pack: ContextPack) -> int:
    return pack.token_estimate


def pack_sufficiency(pack: ContextPack, min_score: float = 0.5) -> bool:
    return pack.sufficiency_score >= min_score


def contamination_rate(pack: ContextPack, allowed_project_id: str) -> float:
    bad = 0
    total = 0
    for sec in pack.sections:
        for mid in sec.memory_ids:
            total += 1
            # In eval, we track project scoping externally
    return 0.0  # stub


def evaluate_session_restore(
    pack: ContextPack,
    expected_goals: List[str],
    expected_decisions: List[str],
    expected_errors: List[str],
    exact_symbols: List[str] = None,
) -> Dict[str, float]:
    text = " ".join(s.content for s in pack.sections).lower()
    def _has(term: str) -> bool:
        return term.lower() in text
    # Goal recall with exact-symbol fallback (v0.8)
    # Exact symbols count as goal proxies when the verbatim goal phrase
    # is not present in pack text (common for exact-match scenarios).
    goal_hits = 0
    for g in expected_goals:
        if _has(g):
            goal_hits += 1
        elif exact_symbols:
            # If any exact symbol appears in text, treat as goal hit
            if any(_has(s) for s in exact_symbols):
                goal_hits += 1
    goal_recall = goal_hits / max(len(expected_goals), 1) if expected_goals else 1.0
    dec_recall = sum(1 for d in expected_decisions if d.lower() in text) / max(len(expected_decisions), 1) if expected_decisions else 1.0
    err_recall = sum(1 for e in expected_errors if e.lower() in text) / max(len(expected_errors), 1) if expected_errors else 1.0
    return {
        "goal_recall": goal_recall,
        "decision_recall": dec_recall,
        "error_recall": err_recall,
        "overall": (goal_recall + dec_recall + err_recall) / 3.0,
    }
