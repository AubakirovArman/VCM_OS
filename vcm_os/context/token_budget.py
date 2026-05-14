from typing import Dict

from vcm_os.schemas import TaskType


class TokenBudgetManager:
    def allocate(self, task_type: str, total_budget: int) -> Dict[str, int]:
        # For eval, default budget is 32768, but we want VCM to be aggressive
        # Use smaller allocations to force compression
        task = task_type.lower()
        defaults = {
            "debugging": {
                "system_task": int(total_budget * 0.04),
                "session_state": int(total_budget * 0.03),
                "decisions": int(total_budget * 0.08),
                "errors": int(total_budget * 0.10),
                "code_context": int(total_budget * 0.15),
                "requirements": int(total_budget * 0.04),
                "graph_paths": int(total_budget * 0.03),
                "procedures": int(total_budget * 0.02),
                "open_questions": int(total_budget * 0.02),
                "buffer": int(total_budget * 0.49),
            },
            "architecture": {
                "system_task": int(total_budget * 0.04),
                "session_state": int(total_budget * 0.03),
                "decisions": int(total_budget * 0.15),
                "errors": int(total_budget * 0.02),
                "code_context": int(total_budget * 0.08),
                "requirements": int(total_budget * 0.10),
                "graph_paths": int(total_budget * 0.05),
                "procedures": int(total_budget * 0.02),
                "open_questions": int(total_budget * 0.02),
                "buffer": int(total_budget * 0.49),
            },
            "feature": {
                "system_task": int(total_budget * 0.04),
                "session_state": int(total_budget * 0.03),
                "decisions": int(total_budget * 0.08),
                "errors": int(total_budget * 0.02),
                "code_context": int(total_budget * 0.15),
                "requirements": int(total_budget * 0.10),
                "graph_paths": int(total_budget * 0.03),
                "procedures": int(total_budget * 0.02),
                "open_questions": int(total_budget * 0.02),
                "buffer": int(total_budget * 0.51),
            },
            "research": {
                "system_task": int(total_budget * 0.04),
                "session_state": int(total_budget * 0.02),
                "decisions": int(total_budget * 0.06),
                "errors": int(total_budget * 0.02),
                "code_context": int(total_budget * 0.08),
                "requirements": int(total_budget * 0.06),
                "graph_paths": int(total_budget * 0.05),
                "procedures": int(total_budget * 0.02),
                "open_questions": int(total_budget * 0.03),
                "buffer": int(total_budget * 0.62),
            },
        }
        allocation = defaults.get(task, defaults["feature"])
        # Normalize to exact total
        current = sum(allocation.values())
        diff = total_budget - current
        allocation["buffer"] += diff
        return allocation

    def estimate_tokens(self, text: str) -> int:
        # More aggressive: 1 token ~ 4 chars for code
        if not text:
            return 0
        return max(1, len(text) // 4)
