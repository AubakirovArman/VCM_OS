"""Project-state restoration metrics."""
from typing import Dict, List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.schemas import ContextPack


def project_state_restore(
    pack: ContextPack,
    goals: List[str],
    tasks: List[str],
    constraints: List[str],
    dependencies: List[str],
) -> Dict[str, float]:
    """Weighted F1-like score over multiple project-state dimensions."""
    text = pack_text(pack)
    scores = {
        "goal_recall": substring_recall(text, goals),
        "task_recall": substring_recall(text, tasks),
        "constraint_recall": substring_recall(text, constraints),
        "dependency_recall": substring_recall(text, dependencies),
    }
    weights = {"goal_recall": 0.3, "task_recall": 0.3, "constraint_recall": 0.2, "dependency_recall": 0.2}
    scores["weighted"] = sum(scores[k] * weights[k] for k in weights)
    return scores
