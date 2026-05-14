"""Composite quality score v0.7 — decomposed from aggregate keyword coverage."""
from typing import Dict

from vcm_os.schemas import ContextPack


def quality_v0_7(
    pack: ContextPack,
    exact_symbol_score: float = 0.0,
    decision_score: float = 0.0,
    project_state_score: float = 0.0,
    open_task_score: float = 0.0,
    error_bug_score: float = 0.0,
    file_function_score: float = 0.0,
    stale_suppression_score: float = 1.0,
    citation_score: float = 1.0,
    context_usefulness_score: float = 0.0,
    token_efficiency_score: float = 0.0,
) -> Dict[str, float]:
    """Decomposed quality score with explicit weights.

    Weights are designed so no single dimension can dominate.
    Keyword coverage is no longer a standalone dimension; it is
    distributed across exact_symbol, decision, and project_state.
    """
    weights = {
        "exact_symbol": 0.15,
        "decision": 0.15,
        "project_state": 0.15,
        "open_task": 0.10,
        "error_bug": 0.10,
        "file_function": 0.10,
        "stale_suppression": 0.10,
        "citation": 0.05,
        "context_usefulness": 0.05,
        "token_efficiency": 0.05,
    }
    components = {
        "exact_symbol": exact_symbol_score,
        "decision": decision_score,
        "project_state": project_state_score,
        "open_task": open_task_score,
        "error_bug": error_bug_score,
        "file_function": file_function_score,
        "stale_suppression": stale_suppression_score,
        "citation": citation_score,
        "context_usefulness": context_usefulness_score,
        "token_efficiency": token_efficiency_score,
    }
    total = sum(components[k] * weights[k] for k in weights)
    return {
        "quality_v0_7": total,
        "components": components,
        "weights": weights,
    }
