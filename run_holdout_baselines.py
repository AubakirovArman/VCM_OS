#!/usr/bin/env python3
"""
Run holdout scenarios with full baseline comparison:
VCM, Full Context, RAG, Summary, RawVerbatim, StrongRAG
"""
import json, tempfile
from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def run_all_baselines():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = ExperimentRunner(store, vector_index, sparse_index, writer)
        holdout = load_holdout_scenarios()

        results = {
            "vcm": [],
            "full": [],
            "rag": [],
            "summary": [],
            "raw_verbatim": [],
            "strong_rag": [],
        }
        per_scenario = []

        for sc in holdout:
            runner.ingest_scenario(sc)

            pack_vcm = runner.run_vcm(sc)
            pack_full = runner.run_baseline_full(sc)
            pack_rag = runner.run_baseline_rag(sc)
            pack_summary = runner.run_baseline_summary(sc)
            pack_raw = runner.run_baseline_raw_verbatim(sc)
            pack_strong = runner.run_baseline_strong_rag(sc)

            score_vcm = runner.score_pack(pack_vcm, sc)
            score_full = runner.score_pack(pack_full, sc)
            score_rag = runner.score_pack(pack_rag, sc)
            score_summary = runner.score_pack(pack_summary, sc)
            score_raw = runner.score_pack(pack_raw, sc)
            score_strong = runner.score_pack(pack_strong, sc)

            results["vcm"].append(score_vcm)
            results["full"].append(score_full)
            results["rag"].append(score_rag)
            results["summary"].append(score_summary)
            results["raw_verbatim"].append(score_raw)
            results["strong_rag"].append(score_strong)

            per_scenario.append({
                "scenario": sc.name,
                "vcm_restore": score_vcm["overall_restore"],
                "vcm_tokens": score_vcm["token_usage"],
                "full_restore": score_full["overall_restore"],
                "full_tokens": score_full["token_usage"],
                "rag_restore": score_rag["overall_restore"],
                "rag_tokens": score_rag["token_usage"],
                "summary_restore": score_summary["overall_restore"],
                "summary_tokens": score_summary["token_usage"],
                "raw_restore": score_raw["overall_restore"],
                "raw_tokens": score_raw["token_usage"],
                "strong_restore": score_strong["overall_restore"],
                "strong_tokens": score_strong["token_usage"],
            })

        def _avg(method, key):
            vals = [r[key] for r in results[method]]
            return sum(vals) / max(len(vals), 1)

        summary = {
            "vcm": {
                "restore": _avg("vcm", "overall_restore"),
                "verbatim": _avg("vcm", "overall_verbatim"),
                "exact": _avg("vcm", "overall_exact"),
                "tokens": _avg("vcm", "token_usage"),
                "quality": _avg("vcm", "quality_score"),
                "stale": _avg("vcm", "stale_penalty"),
            },
            "full": {
                "restore": _avg("full", "overall_restore"),
                "tokens": _avg("full", "token_usage"),
                "quality": _avg("full", "quality_score"),
                "stale": _avg("full", "stale_penalty"),
            },
            "rag": {
                "restore": _avg("rag", "overall_restore"),
                "tokens": _avg("rag", "token_usage"),
                "quality": _avg("rag", "quality_score"),
                "stale": _avg("rag", "stale_penalty"),
            },
            "summary": {
                "restore": _avg("summary", "overall_restore"),
                "tokens": _avg("summary", "token_usage"),
                "quality": _avg("summary", "quality_score"),
                "stale": _avg("summary", "stale_penalty"),
            },
            "raw_verbatim": {
                "restore": _avg("raw_verbatim", "overall_restore"),
                "tokens": _avg("raw_verbatim", "token_usage"),
                "quality": _avg("raw_verbatim", "quality_score"),
                "stale": _avg("raw_verbatim", "stale_penalty"),
            },
            "strong_rag": {
                "restore": _avg("strong_rag", "overall_restore"),
                "tokens": _avg("strong_rag", "token_usage"),
                "quality": _avg("strong_rag", "quality_score"),
                "stale": _avg("strong_rag", "stale_penalty"),
            },
            "per_scenario": per_scenario,
        }

        with open("holdout_baseline_comparison.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("=" * 70)
        print("HOLDOUT BASELINE COMPARISON (20 frozen scenarios)")
        print("=" * 70)
        print(f"{'Method':<15} {'Restore':>8} {'Tokens':>8} {'Quality':>8} {'Stale':>8}")
        print("-" * 55)
        for name in ["vcm", "full", "rag", "summary", "raw_verbatim", "strong_rag"]:
            s = summary[name]
            print(f"{name:<15} {s['restore']:>8.3f} {s['tokens']:>8.1f} {s['quality']:>8.3f} {s['stale']:>8.3f}")

        return summary


if __name__ == "__main__":
    run_all_baselines()
