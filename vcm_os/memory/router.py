from typing import Dict

from vcm_os.schemas import MemoryRequest, RetrievalPlan, TaskType


class MemoryRouter:
    def classify_task(self, query: str) -> TaskType:
        q = query.lower()
        if any(k in q for k in ("debug", "fix", "error", "bug", "fail", "traceback", "exception", "crash")):
            return TaskType.DEBUGGING
        if any(k in q for k in ("architect", "design", "refactor", "structure", "adr", "pattern")):
            return TaskType.ARCHITECTURE
        if any(k in q for k in ("implement", "feature", "add ", "create ", "build ", "develop")):
            return TaskType.FEATURE
        if any(k in q for k in ("research", "investigate", "explore", "compare", "analyze")):
            return TaskType.RESEARCH
        return TaskType.GENERAL

    def make_plan(self, request: MemoryRequest) -> RetrievalPlan:
        task = self.classify_task(request.query)
        reqs = request.retrieval_requirements

        plan = RetrievalPlan(
            needs_session=reqs.get("include_session", True),
            needs_project=reqs.get("include_project", True),
            needs_decisions=reqs.get("include_decisions", True),
            needs_errors=reqs.get("include_errors", True),
            needs_code=reqs.get("include_code", True),
            needs_graph=reqs.get("include_graph", False),
            max_graph_hops=reqs.get("max_graph_hops", 2),
        )

        # Task-specific tuning
        if task == TaskType.DEBUGGING:
            plan.needs_errors = True
            plan.needs_decisions = True
            plan.needs_code = True
        elif task == TaskType.ARCHITECTURE:
            plan.needs_decisions = True
            plan.needs_code = False
        elif task == TaskType.FEATURE:
            plan.needs_code = True
            plan.needs_decisions = True
        elif task == TaskType.RESEARCH:
            plan.needs_project = True
            plan.needs_code = False

        return plan

    def estimate_budget(self, task: TaskType) -> Dict[str, int]:
        # Return section allocations for a 32K budget
        budgets = {
            TaskType.DEBUGGING: {
                "system_task": 1500,
                "session_state": 2000,
                "decisions": 2000,
                "errors": 4000,
                "code_context": 12000,
                "requirements": 2000,
                "graph_paths": 2000,
                "procedures": 1000,
                "open_questions": 1000,
                "buffer": 6500,
            },
            TaskType.ARCHITECTURE: {
                "system_task": 1500,
                "session_state": 1500,
                "decisions": 4000,
                "errors": 1000,
                "code_context": 6000,
                "requirements": 4000,
                "graph_paths": 3000,
                "procedures": 1000,
                "open_questions": 1000,
                "buffer": 9000,
            },
            TaskType.FEATURE: {
                "system_task": 1500,
                "session_state": 2000,
                "decisions": 2000,
                "errors": 1000,
                "code_context": 12000,
                "requirements": 4000,
                "graph_paths": 2000,
                "procedures": 1000,
                "open_questions": 1000,
                "buffer": 8500,
            },
            TaskType.RESEARCH: {
                "system_task": 1500,
                "session_state": 1000,
                "decisions": 2000,
                "errors": 1000,
                "code_context": 4000,
                "requirements": 3000,
                "graph_paths": 3000,
                "procedures": 1000,
                "open_questions": 2000,
                "buffer": 12500,
            },
        }
        return budgets.get(task, budgets[TaskType.GENERAL])
