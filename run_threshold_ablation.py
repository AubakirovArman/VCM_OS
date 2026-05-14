"""Threshold ablation for semantic goal matcher.

Tests thresholds: 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
on VCM holdout scenarios to find honest semantic scores.
"""
import json
import tempfile

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_loader import load_holdout_scenarios
from vcm_os.evals.metrics_v0_9 import evaluate_session_restore_v0_9_semantic
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def run_ablation():
    thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = ExperimentRunner(store, vector_index, sparse_index, writer)

        holdout = load_holdout_scenarios()

        results = {}
        for thresh in thresholds:
            semantic_goals = []
            semantic_decs = []
            semantic_overall = []
            print(f"\n--- Threshold = {thresh} ---")
            for sc in holdout:
                runner.ingest_scenario(sc)
                pack = runner.run_vcm(sc)
                sm = evaluate_session_restore_v0_9_semantic(
                    pack, sc.expected_goals, sc.expected_decisions, sc.expected_errors,
                    vector_index, threshold=thresh,
                )
                semantic_goals.append(sm["semantic_goal_recall"])
                semantic_decs.append(sm["semantic_decision_recall"])
                semantic_overall.append(sm["semantic_overall"])

            results[thresh] = {
                "semantic_goal": sum(semantic_goals) / len(semantic_goals),
                "semantic_decision": sum(semantic_decs) / len(semantic_decs),
                "semantic_overall": sum(semantic_overall) / len(semantic_overall),
            }
            print(f"  goal={results[thresh]['semantic_goal']:.3f}  "
                  f"decision={results[thresh]['semantic_decision']:.3f}  "
                  f"overall={results[thresh]['semantic_overall']:.3f}")

        # Summary table
        print("\n" + "=" * 70)
        print("THRESHOLD ABLATION SUMMARY")
        print("=" * 70)
        print(f"{'Threshold':>10s} | {'Goal':>8s} | {'Decision':>10s} | {'Overall':>10s}")
        print("-" * 70)
        for thresh in thresholds:
            r = results[thresh]
            print(f"{thresh:10.2f} | {r['semantic_goal']:8.3f} | {r['semantic_decision']:10.3f} | {r['semantic_overall']:10.3f}")

        with open("threshold_ablation.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nSaved to threshold_ablation.json")


if __name__ == "__main__":
    run_ablation()
