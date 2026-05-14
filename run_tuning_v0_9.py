"""v0.9 tuning scenarios eval (26 scenarios).

Runs VCM, RawVerbatim, StrongRAG on tuning set.
"""
import json
import tempfile

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.metrics_v0_9 import evaluate_session_restore_v0_9_semantic
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def run_tuning():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = ExperimentRunner(store, vector_index, sparse_index, writer)

        scenarios = load_all_scenarios()
        # Exclude holdout and adversarial
        tuning = [s for s in scenarios if not s.name.startswith("holdout_")]
        print(f"Loaded {len(tuning)} tuning scenarios\n")

        results = []
        for sc in tuning:
            runner.ingest_scenario(sc)
            pack_vcm = runner.run_vcm(sc)
            pack_raw = runner.run_baseline_raw_verbatim(sc)
            pack_rag = runner.run_baseline_strong_rag(sc)

            scores_vcm = runner.score_pack(pack_vcm, sc)
            scores_raw = runner.score_pack(pack_raw, sc)
            scores_rag = runner.score_pack(pack_rag, sc)

            # Semantic at honest threshold 0.75
            semantic_vcm = evaluate_session_restore_v0_9_semantic(
                pack_vcm, sc.expected_goals, sc.expected_decisions, sc.expected_errors,
                vector_index, threshold=0.75,
            )

            results.append({
                "scenario": sc.name,
                "vcm": {
                    "restore": scores_vcm["overall_restore"],
                    "restore_verbatim": scores_vcm.get("overall_verbatim", 0),
                    "restore_semantic_75": semantic_vcm.get("semantic_overall", 0),
                    "tokens": scores_vcm["token_usage"],
                    "stale": scores_vcm["stale_penalty"],
                    "quality": scores_vcm.get("quality_v0_9", scores_vcm["quality_v0_7"]),
                },
                "raw_verbatim": {
                    "restore": scores_raw["overall_restore"],
                    "restore_verbatim": scores_raw.get("overall_verbatim", 0),
                    "tokens": scores_raw["token_usage"],
                    "stale": scores_raw["stale_penalty"],
                    "quality": scores_raw.get("quality_v0_9", scores_raw["quality_v0_7"]),
                },
                "strong_rag": {
                    "restore": scores_rag["overall_restore"],
                    "restore_verbatim": scores_rag.get("overall_verbatim", 0),
                    "tokens": scores_rag["token_usage"],
                    "stale": scores_rag["stale_penalty"],
                    "quality": scores_rag.get("quality_v0_9", scores_rag["quality_v0_7"]),
                },
            })
            print(f"  {sc.name:40s} | "
                  f"VCM={scores_vcm['overall_restore']:.2f}/{scores_vcm['token_usage']:3d} "
                  f"RAW={scores_raw['overall_restore']:.2f}/{scores_raw['token_usage']:3d} "
                  f"RAG={scores_rag['overall_restore']:.2f}/{scores_rag['token_usage']:3d}")

        # Summary
        print("\n" + "=" * 80)
        print("TUNING SUMMARY")
        print("=" * 80)
        for method in ["vcm", "raw_verbatim", "strong_rag"]:
            avg_restore = sum(r[method]["restore"] for r in results) / len(results)
            avg_verb = sum(r[method]["restore_verbatim"] for r in results) / len(results)
            avg_tokens = sum(r[method]["tokens"] for r in results) / len(results)
            avg_stale = sum(r[method]["stale"] for r in results) / len(results)
            avg_quality = sum(r[method]["quality"] for r in results) / len(results)
            extra = ""
            if method == "vcm":
                avg_sem = sum(r["vcm"]["restore_semantic_75"] for r in results) / len(results)
                extra = f" sem75={avg_sem:.3f}"
            print(f"{method.upper():12s} | restore={avg_restore:.3f} verb={avg_verb:.3f} "
                  f"tokens={avg_tokens:.1f} stale={avg_stale:.3f} quality={avg_quality:.3f}{extra}")

        with open("tuning_v0_9_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nSaved to tuning_v0_9_results.json")


if __name__ == "__main__":
    run_tuning()
