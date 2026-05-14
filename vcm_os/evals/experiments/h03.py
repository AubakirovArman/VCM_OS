from typing import Any, Dict, List

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario


class H03_ProjectSwitching:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenarios: List[EvalScenario]) -> Dict[str, Any]:
        for sc in scenarios:
            self.runner.ingest_scenario(sc)

        contamination_counts = []
        for sc in scenarios:
            pack = self.runner.run_vcm(sc)
            wrong_project = 0
            for section in pack.sections:
                for mem_id in section.memory_ids:
                    mem = self.runner.store.get_memory(mem_id)
                    if mem and mem.project_id != sc.project_id:
                        wrong_project += 1
            contamination_counts.append(wrong_project)

        total_cross = sum(contamination_counts)
        avg_contamination = total_cross / max(len(contamination_counts), 1)
        return {
            "total_cross_project_memories": total_cross,
            "avg_cross_per_scenario": avg_contamination,
            "contamination_rate": avg_contamination / 50.0,
            "details": contamination_counts,
        }
