from typing import Any, Dict, List

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario


class T10_VCM_vs_FullContext:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenarios: List[EvalScenario]) -> Dict[str, Any]:
        results = {"vcm": [], "full": [], "summary": [], "rag": []}
        per_scenario = []
        for sc in scenarios:
            self.runner.ingest_scenario(sc)
            pack_vcm = self.runner.run_vcm(sc)
            pack_full = self.runner.run_baseline_full(sc)
            pack_summary = self.runner.run_baseline_summary(sc)
            pack_rag = self.runner.run_baseline_rag(sc)

            score_vcm = self.runner.score_pack(pack_vcm, sc)
            score_full = self.runner.score_pack(pack_full, sc)
            score_summary = self.runner.score_pack(pack_summary, sc)
            score_rag = self.runner.score_pack(pack_rag, sc)

            results["vcm"].append(score_vcm)
            results["full"].append(score_full)
            results["summary"].append(score_summary)
            results["rag"].append(score_rag)

            per_scenario.append({
                "scenario": sc.name,
                "vcm_restore": score_vcm["overall_restore"],
                "vcm_tokens": score_vcm["token_usage"],
                "full_restore": score_full["overall_restore"],
                "full_tokens": score_full["token_usage"],
                "summary_restore": score_summary["overall_restore"],
                "summary_tokens": score_summary["token_usage"],
                "rag_restore": score_rag["overall_restore"],
                "rag_tokens": score_rag["token_usage"],
                "vcm_quality": score_vcm["quality_score"],
                "full_quality": score_full["quality_score"],
            })

        def _avg(key: str, method: str) -> float:
            vals = [r[key] for r in results[method]]
            return sum(vals) / max(len(vals), 1)

        return {
            "vcm": {
                "restore": _avg("overall_restore", "vcm"),
                "tokens": _avg("token_usage", "vcm"),
                "keywords": _avg("keyword_coverage", "vcm"),
                "stale": _avg("stale_penalty", "vcm"),
                "quality": _avg("quality_score", "vcm"),
            },
            "full": {
                "restore": _avg("overall_restore", "full"),
                "tokens": _avg("token_usage", "full"),
                "keywords": _avg("keyword_coverage", "full"),
                "stale": _avg("stale_penalty", "full"),
                "quality": _avg("quality_score", "full"),
            },
            "summary": {
                "restore": _avg("overall_restore", "summary"),
                "tokens": _avg("token_usage", "summary"),
                "keywords": _avg("keyword_coverage", "summary"),
                "stale": _avg("stale_penalty", "summary"),
                "quality": _avg("quality_score", "summary"),
            },
            "rag": {
                "restore": _avg("overall_restore", "rag"),
                "tokens": _avg("token_usage", "rag"),
                "keywords": _avg("keyword_coverage", "rag"),
                "stale": _avg("stale_penalty", "rag"),
                "quality": _avg("quality_score", "rag"),
            },
            "per_scenario": per_scenario,
        }
