"""Exact-symbol recall metrics."""
from typing import List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.schemas import ContextPack


def exact_symbol_recall(pack: ContextPack, gold_symbols: List[str]) -> float:
    """Fraction of required exact symbols present in pack text."""
    return substring_recall(pack_text(pack), gold_symbols)
