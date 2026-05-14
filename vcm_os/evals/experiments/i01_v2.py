"""I01 Project State Restore v2 — evaluates PSO v2 fields."""
from typing import Any, Dict

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario


class I01_ProjectStateRestoreV2:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenario: EvalScenario) -> Dict[str, Any]:
        self.runner.ingest_scenario(scenario)
        pack = self.runner.run_vcm(scenario, override_query=scenario.test_query)
        score = self.runner.score_pack(pack, scenario)

        # PSO v2 specific checks
        pso = self.runner.pso_store.load(scenario.project_id)
        pso_text = ""
        if pso:
            pso_text = " ".join([
                pso.project_phase,
                pso.current_branch,
                pso.current_milestone,
                *pso.blocked_tasks,
                pso.test_status,
                pso.deployment_status,
                *pso.active_experiments,
                *pso.risk_register,
            ]).lower()

        pack_text = " ".join(s.content.lower() for s in pack.sections)

        # Check project-state keywords in pack
        pso_keywords = []
        if pso:
            if pso.project_phase:
                pso_keywords.append(("phase", pso.project_phase))
            if pso.current_branch:
                pso_keywords.append(("branch", pso.current_branch))
            if pso.current_milestone:
                pso_keywords.append(("milestone", pso.current_milestone))
            for bt in pso.blocked_tasks:
                pso_keywords.append(("blocked", bt))
            for risk in pso.risk_register:
                pso_keywords.append(("risk", risk))

        pso_hits = 0
        for key, val in pso_keywords:
            if val.lower() in pack_text:
                pso_hits += 1

        pso_recall = pso_hits / max(len(pso_keywords), 1)

        # Blend with overall restore
        blended = (score["overall_restore"] * 0.5) + (pso_recall * 0.5)

        return {
            "restore_accuracy": score["overall_restore"],
            "pso_recall": pso_recall,
            "blended_score": blended,
            "decision_recall": score["decision_recall"],
            "error_recall": score["error_recall"],
            "token_usage": score["token_usage"],
            "sufficiency": pack.sufficiency_score,
            "pso_fields_found": pso_hits,
            "pso_fields_total": len(pso_keywords),
        }
