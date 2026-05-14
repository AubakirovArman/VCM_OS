"""v0.9 comparison: VCM vs RawVerbatim vs StrongRAG vs Full Context.

Runs all 4 methods on the 20 frozen holdout scenarios and produces
a side-by-side comparison table.
"""
import json
import tempfile

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_loader import load_holdout_scenarios
from vcm_os.evals.metrics_v0_9 import evaluate_session_restore_v0_9_semantic
from vcm_os.evals.mutation_log import MutationLog
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def run_comparison():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = ExperimentRunner(store, vector_index, sparse_index, writer)

        holdout = load_holdout_scenarios()
        print(f"Loaded {len(holdout)} holdout scenarios\n")

        # Validate against mutation log
        log = MutationLog.load()
        validation = log.validate_against_run([s.name for s in holdout])
        print(f"Frozen validation: all_frozen_present={validation['all_frozen_present']}\n")

        results = []
        for sc in holdout:
            runner.ingest_scenario(sc)

            # Run all 4 methods
            pack_vcm = runner.run_vcm(sc)
            pack_raw = runner.run_baseline_raw_verbatim(sc)
            pack_rag = runner.run_baseline_strong_rag(sc)
            pack_full = runner.run_baseline_full(sc)

            # Score all 4
            scores_vcm = runner.score_pack(pack_vcm, sc)
            scores_raw = runner.score_pack(pack_raw, sc)
            scores_rag = runner.score_pack(pack_rag, sc)
            scores_full = runner.score_pack(pack_full, sc)

            # Semantic evaluation (v0.9)
            semantic_vcm = evaluate_session_restore_v0_9_semantic(
                pack_vcm, sc.expected_goals, sc.expected_decisions, sc.expected_errors,
                vector_index, threshold=0.65,
            )

            results.append({
                "scenario": sc.name,
                "vcm": {
                    "restore": scores_vcm["overall_restore"],
                    "restore_verbatim": scores_vcm.get("overall_verbatim", 0),
                    "restore_semantic": semantic_vcm.get("semantic_overall", 0),
                    "semantic_goal": semantic_vcm.get("semantic_goal_recall", 0),
                    "semantic_decision": semantic_vcm.get("semantic_decision_recall", 0),
                    "tokens": scores_vcm["token_usage"],
                    "stale": scores_vcm["stale_penalty"],
                    "quality": scores_vcm.get("quality_v0_9", scores_vcm["quality_v0_7"]),
                    "rationale": scores_vcm.get("rationale_recall", 0),
                    "project_state": scores_vcm.get("project_state_recall", 0),
                    "exact_symbol": scores_vcm.get("exact_symbol_recall", 0),
                },
                "raw_verbatim": {
                    "restore": scores_raw["overall_restore"],
                    "restore_verbatim": scores_raw.get("overall_verbatim", 0),
                    "tokens": scores_raw["token_usage"],
                    "stale": scores_raw["stale_penalty"],
                    "quality": scores_raw.get("quality_v0_9", scores_raw["quality_v0_7"]),
                    "rationale": scores_raw.get("rationale_recall", 0),
                    "project_state": scores_raw.get("project_state_recall", 0),
                    "exact_symbol": scores_raw.get("exact_symbol_recall", 0),
                },
                "strong_rag": {
                    "restore": scores_rag["overall_restore"],
                    "restore_verbatim": scores_rag.get("overall_verbatim", 0),
                    "tokens": scores_rag["token_usage"],
                    "stale": scores_rag["stale_penalty"],
                    "quality": scores_rag.get("quality_v0_9", scores_rag["quality_v0_7"]),
                    "rationale": scores_rag.get("rationale_recall", 0),
                    "project_state": scores_rag.get("project_state_recall", 0),
                    "exact_symbol": scores_rag.get("exact_symbol_recall", 0),
                },
                "full": {
                    "restore": scores_full["overall_restore"],
                    "restore_verbatim": scores_full.get("overall_verbatim", 0),
                    "tokens": scores_full["token_usage"],
                    "stale": scores_full["stale_penalty"],
                    "quality": scores_full.get("quality_v0_9", scores_full["quality_v0_7"]),
                    "rationale": scores_full.get("rationale_recall", 0),
                    "project_state": scores_full.get("project_state_recall", 0),
                    "exact_symbol": scores_full.get("exact_symbol_recall", 0),
                },
            })

            print(f"  {sc.name:40s} | "
                  f"VCM={scores_vcm['overall_restore']:.2f}/{scores_vcm['token_usage']:3d} "
                  f"Vsem={semantic_vcm.get('semantic_overall', 0):.2f} "
                  f"RAW={scores_raw['overall_restore']:.2f}/{scores_raw['token_usage']:3d} "
                  f"RAG={scores_rag['overall_restore']:.2f}/{scores_rag['token_usage']:3d} "
                  f"FULL={scores_full['overall_restore']:.2f}/{scores_full['token_usage']:3d}")

        # Summary
        print("\n" + "=" * 100)
        print("SUMMARY (avg over 20 holdout scenarios)")
        print("=" * 100)

        for method in ["vcm", "raw_verbatim", "strong_rag", "full"]:
            avg_restore = sum(r[method]["restore"] for r in results) / len(results)
            avg_restore_v = sum(r[method]["restore_verbatim"] for r in results) / len(results)
            avg_tokens = sum(r[method]["tokens"] for r in results) / len(results)
            avg_stale = sum(r[method]["stale"] for r in results) / len(results)
            avg_quality = sum(r[method]["quality"] for r in results) / len(results)
            avg_rationale = sum(r[method]["rationale"] for r in results) / len(results)
            avg_ps = sum(r[method]["project_state"] for r in results) / len(results)
            avg_sym = sum(r[method]["exact_symbol"] for r in results) / len(results)

            print(f"\n{method.upper():12s} | "
                  f"restore={avg_restore:.3f} "
                  f"restore(verb)={avg_restore_v:.3f} "
                  f"tokens={avg_tokens:.1f} "
                  f"stale={avg_stale:.3f} "
                  f"quality={avg_quality:.3f}")
            print(f"             | rationale={avg_rationale:.3f} "
                  f"proj_state={avg_ps:.3f} "
                  f"exact_sym={avg_sym:.3f}")

        # Semantic metrics (VCM only)
        print("\n" + "=" * 100)
        print("SEMANTIC RESTORE (VCM only, embedding-based)")
        print("=" * 100)
        avg_semantic = sum(r["vcm"]["restore_semantic"] for r in results) / len(results)
        avg_sem_goal = sum(r["vcm"]["semantic_goal"] for r in results) / len(results)
        avg_sem_dec = sum(r["vcm"]["semantic_decision"] for r in results) / len(results)
        print(f"VCM semantic overall : {avg_semantic:.3f}")
        print(f"VCM semantic goal    : {avg_sem_goal:.3f}")
        print(f"VCM semantic decision: {avg_sem_dec:.3f}")

        # Per-scenario verbatim comparison (the key v0.9 metric)
        print("\n" + "=" * 100)
        print("VERBATIM RESTORE COMPARISON (VCM vs RawVerbatim vs StrongRAG)")
        print("=" * 100)
        print(f"{'Scenario':<40s} | {'VCM':>6s} | {'RAW':>6s} | {'RAG':>6s} | {'FULL':>6s}")
        print("-" * 100)
        for r in results:
            v = r["vcm"]["restore_verbatim"]
            raw = r["raw_verbatim"]["restore_verbatim"]
            rag = r["strong_rag"]["restore_verbatim"]
            full = r["full"]["restore_verbatim"]
            marker = ""
            if v >= raw and v >= rag:
                marker = " ✓ VCM wins"
            elif raw > v and raw >= rag:
                marker = " ⚠ RAW wins"
            elif rag > v and rag >= raw:
                marker = " ⚠ RAG wins"
            print(f"{r['scenario']:<40s} | {v:6.3f} | {raw:6.3f} | {rag:6.3f} | {full:6.3f}{marker}")

        # Save
        with open("v0_9_comparison.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nSaved to v0_9_comparison.json")


if __name__ == "__main__":
    run_comparison()
