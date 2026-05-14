"""v0.9 component metrics with separated recall types."""
from typing import Dict, List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.evals.metrics_v0_9 import evaluate_session_restore_v0_9
from vcm_os.schemas import ContextPack


def exact_symbol_recall(pack: ContextPack, gold_symbols: List[str]) -> float:
    return substring_recall(pack_text(pack), gold_symbols)


def decision_recall(pack: ContextPack, expected_decisions: List[str]) -> float:
    return substring_recall(pack_text(pack), expected_decisions)


def decision_correctness(pack: ContextPack, expected_decisions: List[str]) -> float:
    text = pack_text(pack)
    hits = sum(1 for d in expected_decisions if d.lower() in text)
    return hits / max(len(expected_decisions), 1)


def error_bug_restore(pack: ContextPack, expected_errors: List[str]) -> float:
    return substring_recall(pack_text(pack), expected_errors)


def project_state_restore(
    pack: ContextPack,
    expected_goals: List[str],
    expected_decisions: List[str],
    expected_errors: List[str],
) -> Dict[str, float]:
    pso_text = ""
    for s in pack.sections:
        if s.section_name in ("project_state", "exact_symbols"):
            pso_text += " " + s.content.lower()
    all_checks = list(expected_goals) + list(expected_decisions) + list(expected_errors)
    hits = sum(1 for c in all_checks if c.lower() in pso_text)
    return {"weighted": hits / max(len(all_checks), 1)}


def file_function_relevance(pack: ContextPack, expected_files: List[str], expected_functions: List[str]) -> float:
    text = pack_text(pack)
    terms = list(expected_files) + list(expected_functions)
    return substring_recall(text, terms)


def stale_suppression_rate(pack: ContextPack, stale_facts: List[str]) -> float:
    if not stale_facts:
        return 1.0
    text = pack_text(pack)
    hits = sum(1 for sf in stale_facts if sf.lower() in text)
    return 1.0 - (hits / len(stale_facts))


def token_efficiency(pack: ContextPack, restore_score: float) -> Dict[str, float]:
    tokens = pack.token_estimate
    efficiency = restore_score / max(tokens / 84.0, 1.0)
    return {"efficiency_score": efficiency, "reduction_ratio": 1.0}


def rationale_recall(pack: ContextPack, expected_rationales: List[str] = None) -> float:
    """Check if expected rationales appear in pack text.
    Falls back to marker detection if no expected rationales provided."""
    text = pack_text(pack)
    if expected_rationales:
        hits = sum(1 for r in expected_rationales if r.lower() in text)
        return hits / len(expected_rationales)
    markers = ["why", "because", "rationale", "reason", "tradeoff", "alternative", "instead of"]
    return 1.0 if any(m in text for m in markers) else 0.0


def quality_v0_9(
    pack: ContextPack,
    exact_symbol_score: float,
    decision_score: float,
    project_state_score: float,
    open_task_score: float,
    error_bug_score: float,
    file_function_score: float,
    stale_suppression_score: float,
    rationale_score: float,
    token_efficiency_score: float,
) -> Dict[str, float]:
    """v0.9 composite with rationale instead of citation/context_usefulness."""
    weights = {
        "exact_symbol": 0.15,
        "decision": 0.15,
        "project_state": 0.15,
        "error_bug": 0.10,
        "open_task": 0.10,
        "file_function": 0.10,
        "stale_suppression": 0.10,
        "rationale": 0.05,
        "token_efficiency": 0.10,
    }
    components = {
        "exact_symbol": exact_symbol_score,
        "decision": decision_score,
        "project_state": project_state_score,
        "error_bug": error_bug_score,
        "open_task": open_task_score,
        "file_function": file_function_score,
        "stale_suppression": stale_suppression_score,
        "rationale": rationale_score,
        "token_efficiency": token_efficiency_score,
    }
    score = sum(weights.get(k, 0) * v for k, v in components.items())
    return {"quality_v0_9": score, "components": components}
