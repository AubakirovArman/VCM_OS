"""v0.9 separated evaluator metrics.

Splits goal recall into:
- goal_recall_verbatim: strict substring matching (as before v0.8)
- goal_recall_semantic: embedding-based or LLM judge (stub for now)
- goal_recall_exact_symbol: exact symbol presence in pack text
- decision_recall: verbatim decision matching
- rationale_recall: decision rationale / tradeoffs preserved (stub)
- error_recall: verbatim error matching
- project_state_recall: active goals + open tasks + latest decisions present
"""
from typing import Dict, List, Optional

from vcm_os.schemas import ContextPack
from vcm_os.storage.vector_index import VectorIndex


def evaluate_session_restore_v0_9_semantic(
    pack: ContextPack,
    expected_goals: List[str],
    expected_decisions: List[str],
    expected_errors: List[str],
    vector_index: VectorIndex,
    threshold: float = 0.65,
) -> Dict[str, float]:
    """v0.9 semantic evaluator using embeddings."""
    from vcm_os.evals.semantic_matcher import SemanticGoalMatcher
    matcher = SemanticGoalMatcher(vector_index, threshold=threshold)

    goal_result = matcher.match_goals(pack, expected_goals)
    dec_result = matcher.match_decisions(pack, expected_decisions)

    # Error recall remains verbatim (errors are exact strings)
    text = " ".join(s.content for s in pack.sections).lower()
    err_recall = sum(1 for e in expected_errors if e.lower() in text) / max(len(expected_errors), 1) if expected_errors else 1.0

    semantic_overall = (goal_result["semantic_goal_recall"] + dec_result["semantic_decision_recall"] + err_recall) / 3.0

    return {
        "semantic_goal_recall": goal_result["semantic_goal_recall"],
        "semantic_decision_recall": dec_result["semantic_decision_recall"],
        "error_recall": err_recall,
        "semantic_overall": semantic_overall,
        "per_goal_scores": goal_result.get("per_goal_scores", {}),
        "per_decision_scores": dec_result.get("per_decision_scores", {}),
    }


def evaluate_session_restore_v0_9(
    pack: ContextPack,
    expected_goals: List[str],
    expected_decisions: List[str],
    expected_errors: List[str],
    exact_symbols: List[str] = None,
) -> Dict[str, float]:
    """Separated evaluator: verbatim vs semantic vs exact-symbol vs rationale.

    Returns individual metrics so caller can compute composite how they want.
    """
    text = " ".join(s.content for s in pack.sections).lower()

    def _has(term: str) -> bool:
        return term.lower() in text

    # 1. Verbatim goal recall (strict, no fallback)
    goal_verbatim_hits = sum(1 for g in expected_goals if _has(g))
    goal_recall_verbatim = goal_verbatim_hits / max(len(expected_goals), 1) if expected_goals else 1.0

    # 2. Exact-symbol goal recall (fallback when verbatim fails)
    goal_exact_hits = 0
    for g in expected_goals:
        if _has(g):
            goal_exact_hits += 1
        elif exact_symbols:
            if any(_has(s) for s in exact_symbols):
                goal_exact_hits += 1
    goal_recall_exact_symbol = goal_exact_hits / max(len(expected_goals), 1) if expected_goals else 1.0

    # 3. Semantic goal recall (placeholder — would need embedding judge)
    # For now: same as exact-symbol, since we don't have semantic judge yet
    goal_recall_semantic = goal_recall_exact_symbol

    # 4. Decision recall (verbatim)
    dec_recall = sum(1 for d in expected_decisions if d.lower() in text) / max(len(expected_decisions), 1) if expected_decisions else 1.0

    # 5. Rationale recall (placeholder)
    # Would check if decision rationale / tradeoffs / alternatives are present.
    # For now, approximate by checking if any decision-adjacent text has "why", "because", "rationale".
    rationale_recall = 0.0  # stub: needs LLM judge or structured rationale extraction
    if expected_decisions:
        rationale_markers = ["why", "because", "rationale", "reason", "tradeoff", "alternative", "instead of"]
        has_rationale = any(marker in text for marker in rationale_markers)
        rationale_recall = 1.0 if has_rationale else 0.0

    # 6. Error recall (verbatim)
    err_recall = sum(1 for e in expected_errors if e.lower() in text) / max(len(expected_errors), 1) if expected_errors else 1.0

    # 7. Project state recall: check if PSO section has active goals, decisions, bugs
    pso_text = ""
    for s in pack.sections:
        if s.section_name in ("project_state", "exact_symbols"):
            pso_text += " " + s.content.lower()
    pso_hits = 0
    pso_checks = list(expected_goals) + list(expected_decisions) + list(expected_errors)
    for check in pso_checks:
        if check.lower() in pso_text:
            pso_hits += 1
    project_state_recall = pso_hits / max(len(pso_checks), 1) if pso_checks else 1.0

    # Overall: use VERBATIM goal recall (honest), not exact-symbol fallback
    overall_verbatim = (goal_recall_verbatim + dec_recall + err_recall) / 3.0
    overall_exact = (goal_recall_exact_symbol + dec_recall + err_recall) / 3.0

    return {
        "goal_recall_verbatim": goal_recall_verbatim,
        "goal_recall_exact_symbol": goal_recall_exact_symbol,
        "goal_recall_semantic": goal_recall_semantic,
        "decision_recall": dec_recall,
        "rationale_recall": rationale_recall,
        "error_recall": err_recall,
        "project_state_recall": project_state_recall,
        "overall_verbatim": overall_verbatim,
        "overall_exact": overall_exact,
    }


def evaluate_session_restore(
    pack: ContextPack,
    expected_goals: List[str],
    expected_decisions: List[str],
    expected_errors: List[str],
    exact_symbols: List[str] = None,
) -> Dict[str, float]:
    """Legacy evaluator v0.8 (backward compatible).
    Uses exact-symbol fallback for goal recall.
    """
    text = " ".join(s.content for s in pack.sections).lower()
    def _has(term: str) -> bool:
        return term.lower() in text

    goal_hits = 0
    for g in expected_goals:
        if _has(g):
            goal_hits += 1
        elif exact_symbols:
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
