#!/usr/bin/env python3
"""Dogfooding harness: ingest real codebase sessions and evaluate.

Usage:
    python scripts/dogfood_harness.py --repos /path/to/repo1 /path/to/repo2
    python scripts/dogfood_harness.py --default-repos
    python scripts/dogfood_harness.py --default-repos --eval
"""

import argparse
import json
import sys
from pathlib import Path

# Add VCM_OS to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.real_codebase_generator import generate_real_codebase_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


DEFAULT_REPOS = [
    "/mnt/hf_model_weights/arman/3bit/wal",
    "/mnt/hf_model_weights/arman/3bit/archiv.org",
]


def run_dogfood(repos, commits_per_scenario=3, run_eval=False):
    print("=" * 70)
    print("VCM-OS Dogfooding Harness")
    print("=" * 70)

    scenarios = generate_real_codebase_scenarios(repos, commits_per_scenario=commits_per_scenario)
    print(f"\nGenerated {len(scenarios)} scenarios from {len(repos)} repos")
    for s in scenarios[:5]:
        print(f"  {s.name}: {len(s.events)} events")
    if len(scenarios) > 5:
        print(f"  ... and {len(scenarios) - 5} more")

    store = SQLiteStore()
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    # Ingest all scenarios
    print("\n--- Ingesting scenarios ---")
    for s in scenarios:
        runner.ingest_scenario(s)
        print(f"  Ingested: {s.name}")

    if not run_eval:
        print("\n--- Ingestion complete ---")
        print(f"Total scenarios ingested: {len(scenarios)}")
        print("Run with --eval to evaluate restore metrics")
        return

    # Evaluate
    print("\n--- Evaluating scenarios ---")
    results = []
    for s in scenarios:
        pack = runner.run_vcm(s, override_query=s.test_query)
        score = runner.score_pack(pack, s)
        results.append({
            "scenario": s.name,
            "project_id": s.project_id,
            "restore": score.get("overall_restore", 0.0),
            "quality": score.get("quality_score", 0.0),
            "tokens": score.get("token_usage", 0),
            "keyword_coverage": score.get("keyword_coverage", 0.0),
            "critical_survival": score.get("critical_survival", 0.0),
        })
        print(f"  {s.name}: restore={results[-1]['restore']:.3f} quality={results[-1]['quality']:.3f} tokens={results[-1]['tokens']}")

    # Summary stats
    restores = [r["restore"] for r in results]
    qualities = [r["quality"] for r in results]
    tokens = [r["tokens"] for r in results]

    import statistics
    summary = {
        "scenario_count": len(scenarios),
        "repos": [str(r) for r in repos],
        "avg_restore": statistics.mean(restores) if restores else 0.0,
        "median_restore": statistics.median(restores) if restores else 0.0,
        "min_restore": min(restores) if restores else 0.0,
        "max_restore": max(restores) if restores else 0.0,
        "avg_quality": statistics.mean(qualities) if qualities else 0.0,
        "avg_tokens": statistics.mean(tokens) if tokens else 0.0,
        "results": results,
    }

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Scenarios:      {summary['scenario_count']}")
    print(f"Avg restore:    {summary['avg_restore']:.3f}")
    print(f"Median restore: {summary['median_restore']:.3f}")
    print(f"Min restore:    {summary['min_restore']:.3f}")
    print(f"Max restore:    {summary['max_restore']:.3f}")
    print(f"Avg quality:    {summary['avg_quality']:.3f}")
    print(f"Avg tokens:     {summary['avg_tokens']:.1f}")
    print("=" * 70)

    # Save results
    out_path = Path("dogfood_results.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Dogfooding Harness")
    parser.add_argument("--repos", nargs="+", help="Paths to git repositories")
    parser.add_argument("--default-repos", action="store_true", help="Use default repositories")
    parser.add_argument("--commits-per-scenario", type=int, default=3, help="Commits per scenario")
    parser.add_argument("--eval", action="store_true", help="Run evaluation after ingestion")
    args = parser.parse_args()

    repos = args.repos if args.repos else []
    if args.default_repos:
        repos = DEFAULT_REPOS

    if not repos:
        parser.print_help()
        sys.exit(1)

    run_dogfood(repos, commits_per_scenario=args.commits_per_scenario, run_eval=args.eval)


if __name__ == "__main__":
    main()
