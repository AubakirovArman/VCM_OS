from typing import Any, Dict

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario


class S05_FalseMemory:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenario: EvalScenario) -> Dict[str, Any]:
        self.runner.ingest_scenario(scenario)

        mems = self.runner.store.get_memories(project_id=scenario.project_id, memory_type="decision")
        false_memories = []
        rejected_memories = []
        for m in mems:
            text = (m.raw_text or "").lower()
            if "postgresql" in text and "read replica" in text:
                false_memories.append(m.memory_id)
                if m.validity == "rejected":
                    rejected_memories.append(m.memory_id)

        sqlite_active = False
        for m in mems:
            text = (m.raw_text or "").lower()
            if "sqlite" in text and m.validity == "active":
                sqlite_active = True

        return {
            "false_decisions_found": len(false_memories),
            "false_decisions_rejected": len(rejected_memories),
            "sqlite_active": sqlite_active,
            "false_memory_rate": len(false_memories) / max(len(mems), 1),
        }
