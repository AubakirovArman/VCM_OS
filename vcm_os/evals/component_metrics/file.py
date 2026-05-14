"""File/function relevance metrics."""
from typing import List

from vcm_os.evals.component_metrics.core import pack_text, substring_recall
from vcm_os.schemas import ContextPack


def file_function_relevance(pack: ContextPack, gold_files: List[str], gold_functions: List[str]) -> float:
    """Recall of correct files and functions in pack text."""
    text = pack_text(pack)
    file_score = substring_recall(text, gold_files)
    func_score = substring_recall(text, gold_functions)
    return 0.5 * file_score + 0.5 * func_score
