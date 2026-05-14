from typing import Any, Dict

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario


class I01_ProjectStateRestore:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenario: EvalScenario) -> Dict[str, Any]:
        self.runner.ingest_scenario(scenario)
        pack = self.runner.run_vcm(scenario, override_query=scenario.test_query)
        score = self.runner.score_pack(pack, scenario)

        return {
            "restore_accuracy": score["overall_restore"],
            "decision_recall": score["decision_recall"],
            "error_recall": score["error_recall"],
            "token_usage": score["token_usage"],
            "sufficiency": pack.sufficiency_score,
        }
