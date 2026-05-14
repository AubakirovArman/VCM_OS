"""Decision-related component metrics."""
from typing import List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.schemas import ContextPack


def decision_recall(pack: ContextPack, active_decisions: List[str]) -> float:
    """Fraction of active decisions found in pack text."""
    return substring_recall(pack_text(pack), active_decisions)


def decision_correctness(pack: ContextPack, correct_decisions: List[str], wrong_decisions: List[str]) -> float:
    """Score based on presence of correct decisions and absence of wrong/rejected ones."""
    text = pack_text(pack)
    correct_hits = sum(1 for d in correct_decisions if d.lower() in text)
    wrong_hits = sum(1 for d in wrong_decisions if d.lower() in text)
    correct_score = correct_hits / max(len(correct_decisions), 1)
    wrong_penalty = wrong_hits / max(len(wrong_decisions), 1) if wrong_decisions else 0.0
    return max(0.0, correct_score - wrong_penalty)
