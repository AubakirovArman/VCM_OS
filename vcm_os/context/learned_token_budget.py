"""Learned token budget manager — data-driven section allocation.

Based on pack_analysis.json findings:
- intents: 67% success (boost)
- decisions: 47% success (slight reduce)
- code_change: 46% success (slight reduce)
- errors: 43% success (reduce for non-debug)
- requirements: 40% success (reduce)
"""
from typing import Dict

from vcm_os.context.token_budget import TokenBudgetManager


class LearnedTokenBudgetManager(TokenBudgetManager):
    """Drop-in replacement for TokenBudgetManager."""

    def allocate(self, task_type: str, total_budget: int) -> Dict[str, int]:
        base = super().allocate(task_type, total_budget)

        # Data-driven multipliers from pack_analysis.json
        multipliers = {
            "intents": 1.3,
            "requirements": 0.85,
            "decisions": 0.9,
            "errors": 0.85 if task_type != "debugging" else 1.0,
            "code_context": 0.9,
            "reflections": 0.8,
            "procedures": 0.8,
            "open_questions": 0.8,
            "graph_paths": 0.8,
        }

        adjusted = {}
        for section, budget in base.items():
            mult = multipliers.get(section, 1.0)
            adjusted[section] = int(budget * mult)

        # Re-normalize to exact total
        current = sum(adjusted.values())
        diff = total_budget - current
        if "buffer" in adjusted:
            adjusted["buffer"] += diff
        else:
            adjusted[list(adjusted.keys())[-1]] += diff

        return adjusted
