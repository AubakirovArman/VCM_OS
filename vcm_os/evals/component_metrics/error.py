"""Error/bug restoration metrics."""
from typing import Dict, List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.schemas import ContextPack


def error_bug_restore(
    pack: ContextPack,
    errors: List[str],
    root_causes: List[str],
    fixes: List[str],
) -> Dict[str, float]:
    """Weighted recall over error text, root cause, and fix."""
    text = pack_text(pack)
    scores = {
        "error_recall": substring_recall(text, errors),
        "root_cause_recall": substring_recall(text, root_causes),
        "fix_recall": substring_recall(text, fixes),
    }
    weights = {"error_recall": 0.4, "root_cause_recall": 0.35, "fix_recall": 0.25}
    scores["weighted"] = sum(scores[k] * weights[k] for k in weights)
    return scores
