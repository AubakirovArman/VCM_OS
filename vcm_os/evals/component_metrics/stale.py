"""Stale suppression metrics."""
from typing import List

from vcm_os.evals.component_metrics.core import pack_text
from vcm_os.schemas import ContextPack


def stale_suppression_rate(pack: ContextPack, stale_facts: List[str]) -> float:
    """Fraction of stale facts correctly excluded from pack text."""
    from vcm_os.evals.component_metrics.core import stale_penalty
    penalty = stale_penalty(pack_text(pack), stale_facts)
    return 1.0 - penalty
