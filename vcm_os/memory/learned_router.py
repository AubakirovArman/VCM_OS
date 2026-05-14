"""Learned router v0.10 — frequency-based budget adjustment from eval data.

Based on pack_analysis.json:
- intents: 67% success rate (boost budget)
- protected_evidence: 100% success (always enable)
- exact_symbols: 57% success (boost budget)
- decisions: 47% success (slightly reduce)
- code_change: 46% success (slightly reduce)
- errors: 43% success (reduce for non-debugging)
"""
from typing import Dict

from vcm_os.memory.router import MemoryRouter
from vcm_os.schemas import TaskType


class LearnedRouter(MemoryRouter):
    """Drop-in replacement for MemoryRouter with data-driven budget tuning."""

    def estimate_budget(self, task: TaskType) -> Dict[str, int]:
        base = super().estimate_budget(task)

        # Data-driven adjustments from pack_analysis.json
        # Boost high-success sections, reduce low-success sections
        multipliers = {
            "intents": 1.3,  # 67% success rate
            "exact_symbols": 1.2,  # 57% success rate
            "protected_evidence": 1.5,  # 100% success rate
            "decisions": 0.9,  # 47% success rate
            "errors": 0.85 if task != TaskType.DEBUGGING else 1.0,  # 43% general, keep for debug
            "code_context": 0.9,  # 46% success rate
            "requirements": 0.85,  # 40% success rate
            "reflections": 0.8,  # low success
            "procedures": 0.8,  # low success
            "open_questions": 0.8,  # low success
            "facts": 0.8,  # low success
        }

        adjusted = {}
        for section, budget in base.items():
            mult = multipliers.get(section, 1.0)
            adjusted[section] = int(budget * mult)

        # Re-normalize to exact total
        total = sum(adjusted.values())
        orig_total = sum(base.values())
        diff = orig_total - total
        if "buffer" in adjusted:
            adjusted["buffer"] += diff
        else:
            adjusted[list(adjusted.keys())[-1]] += diff

        return adjusted
