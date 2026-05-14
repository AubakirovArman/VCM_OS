from typing import Any, Dict

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario
from vcm_os.schemas import MemoryRequest


class F03_HybridRetrieval:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def run(self, scenario: EvalScenario) -> Dict[str, Any]:
        self.runner.ingest_scenario(scenario)

        pack_hybrid = self.runner.run_vcm(scenario)
        score_hybrid = self.runner.score_pack(pack_hybrid, scenario)

        vec_results = self.runner.vector_index.search(scenario.test_query, top_k=50)
        candidates_vec = []
        for mem_id, score in vec_results:
            mem = self.runner.store.get_memory(mem_id)
            if mem and mem.project_id == scenario.project_id:
                candidates_vec.append(mem)

        request = MemoryRequest(
            project_id=scenario.project_id,
            query=scenario.test_query,
            task_type="general",
        )
        pack_vec = self.runner.pack_builder.build(request, candidates_vec)
        score_vec = self.runner.score_pack(pack_vec, scenario)

        return {
            "scenario": scenario.name,
            "hybrid_restore": score_hybrid["overall_restore"],
            "vector_only_restore": score_vec["overall_restore"],
            "hybrid_quality": score_hybrid["quality_score"],
            "vector_only_quality": score_vec["quality_score"],
            "hybrid_tokens": score_hybrid["token_usage"],
            "vector_only_tokens": score_vec["token_usage"],
            "hybrid_stale": score_hybrid["stale_penalty"],
            "vector_only_stale": score_vec["stale_penalty"],
            "restore_improvement": score_hybrid["overall_restore"] - score_vec["overall_restore"],
            "quality_improvement": score_hybrid["quality_score"] - score_vec["quality_score"],
            "stale_reduction": score_vec["stale_penalty"] - score_hybrid["stale_penalty"],
        }
