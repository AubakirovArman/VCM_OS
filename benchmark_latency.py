#!/usr/bin/env python3
"""VCM-OS Latency Benchmark.

Measures retrieval, pack build, tool ingestion, and PSO update latencies.

Usage:
    python benchmark_latency.py --scenario search_optimization_regression
    python benchmark_latency.py --all
"""

import argparse
import statistics
import sys
import time
from typing import Dict, List

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.memory.project_state.extractor import ProjectStateExtractor
from vcm_os.memory.writer import MemoryWriter
from vcm_os.memory.writer.tool_ingestor import ToolResultIngestor
from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


class LatencyBenchmark:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def benchmark_retrieval(self, request: MemoryRequest, n_warmup: int = 1, n_runs: int = 10) -> Dict:
        """Benchmark vector, sparse, and hybrid retrieval."""
        # Warmup
        for _ in range(n_warmup):
            self.runner.vector_index.search(request.query, top_k=20)
            self.runner.sparse_index.search(request.query, top_k=20)
            plan = self.runner.router.make_plan(request)
            self.runner.reader.retrieve(request, plan)

        # Vector
        vector_times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            self.runner.vector_index.search(request.query, top_k=20)
            vector_times.append(time.perf_counter() - t0)

        # Sparse
        sparse_times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            self.runner.sparse_index.search(request.query, top_k=20)
            sparse_times.append(time.perf_counter() - t0)

        # Hybrid (full retrieval pipeline)
        hybrid_times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            plan = self.runner.router.make_plan(request)
            candidates = self.runner.reader.retrieve(request, plan)
            self.runner.scorer.rerank(candidates, request)
            hybrid_times.append(time.perf_counter() - t0)

        def _stats(times):
            return {
                "p50_ms": statistics.median(times) * 1000,
                "p95_ms": statistics.quantiles(times, n=20)[18] * 1000 if len(times) >= 20 else max(times) * 1000,
                "mean_ms": statistics.mean(times) * 1000,
                "min_ms": min(times) * 1000,
                "max_ms": max(times) * 1000,
            }

        return {
            "vector": _stats(vector_times),
            "sparse": _stats(sparse_times),
            "hybrid": _stats(hybrid_times),
        }

    def benchmark_pack_build(self, request: MemoryRequest, n_runs: int = 10) -> Dict:
        """Benchmark context pack building."""
        plan = self.runner.router.make_plan(request)
        candidates = self.runner.reader.retrieve(request, plan)
        scored = self.runner.scorer.rerank(candidates, request)

        times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            self.runner.pack_builder.build(request, [m for m, _ in scored[:50]])
            times.append(time.perf_counter() - t0)

        return {
            "p50_ms": statistics.median(times) * 1000,
            "p95_ms": statistics.quantiles(times, n=20)[18] * 1000 if len(times) >= 20 else max(times) * 1000,
            "mean_ms": statistics.mean(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
        }

    def benchmark_pso_update(self, project_id: str, n_runs: int = 10) -> Dict:
        """Benchmark PSO extraction and update."""
        extractor = ProjectStateExtractor()
        mems = self.runner.store.get_memories(project_id=project_id, limit=200)

        times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            pso = extractor.extract(mems)
            times.append(time.perf_counter() - t0)

        return {
            "p50_ms": statistics.median(times) * 1000,
            "p95_ms": statistics.quantiles(times, n=20)[18] * 1000 if len(times) >= 20 else max(times) * 1000,
            "mean_ms": statistics.mean(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
        }


def run_benchmark(scenario=None, all_scenarios=False):
    store = SQLiteStore()
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)
    bench = LatencyBenchmark(runner)

    scenarios = []
    if all_scenarios:
        scenarios = load_all_scenarios()
    elif scenario:
        scenarios = [scenario]
    else:
        # Default: use first holdout scenario
        all_s = load_all_scenarios()
        scenarios = [all_s[0]] if all_s else []

    results = []
    for sc in scenarios:
        runner.ingest_scenario(sc)
        request = MemoryRequest(
            project_id=sc.project_id,
            query=sc.test_query,
            required_terms=list(sc.critical_gold) + list(sc.protected_terms),
        )

        print(f"\n{'='*70}")
        print(f"Benchmarking: {sc.name}")
        print(f"Project: {sc.project_id}")
        print(f"Query: {sc.test_query[:60]}")
        print(f"{'='*70}")

        print("\n--- Retrieval Latency ---")
        ret = bench.benchmark_retrieval(request, n_runs=10)
        for name, stats in ret.items():
            print(f"  {name:10}  p50={stats['p50_ms']:7.2f}ms  p95={stats['p95_ms']:7.2f}ms  mean={stats['mean_ms']:7.2f}ms")

        print("\n--- Pack Build Latency ---")
        pack = bench.benchmark_pack_build(request, n_runs=10)
        print(f"  p50={pack['p50_ms']:7.2f}ms  p95={pack['p95_ms']:7.2f}ms  mean={pack['mean_ms']:7.2f}ms")

        print("\n--- PSO Update Latency ---")
        pso = bench.benchmark_pso_update(sc.project_id, n_runs=10)
        print(f"  p50={pso['p50_ms']:7.2f}ms  p95={pso['p95_ms']:7.2f}ms  mean={pso['mean_ms']:7.2f}ms")

        # Tool ingestion micro-benchmark
        print("\n--- Tool Ingestion Latency ---")
        ingestor = ToolResultIngestor()
        pytest_event = EventRecord(
            event_id="evt_test_pytest",
            project_id=sc.project_id,
            event_type="tool_call",
            payload={"tool_name": "pytest", "content": """
============================= test session starts ==============================
platform linux -- Python 3.13.9, pytest-9.0.3
rootdir: /project
collected 10 items

tests/test_auth.py::test_login PASSED
tests/test_auth.py::test_refresh PASSED
tests/test_auth.py::test_logout PASSED

============================== 3 passed in 0.12s ===============================
"""},
        )
        git_event = EventRecord(
            event_id="evt_test_git",
            project_id=sc.project_id,
            event_type="tool_call",
            payload={"tool_name": "git_diff", "content": """
diff --git a/auth.py b/auth.py
index 123..456 100644
--- a/auth.py
+++ b/auth.py
@@ -10,5 +10,5 @@ def refresh():
-    return old_token
+    return new_token
"""},
        )

        t_times = []
        for _ in range(10):
            t0 = time.perf_counter()
            ingestor.ingest(pytest_event)
            ingestor.ingest(git_event)
            t_times.append(time.perf_counter() - t0)

        t_stats = {
            "p50_ms": statistics.median(t_times) * 1000,
            "mean_ms": statistics.mean(t_times) * 1000,
            "max_ms": max(t_times) * 1000,
        }
        print(f"  p50={t_stats['p50_ms']:7.2f}ms  mean={t_stats['mean_ms']:7.2f}ms  max={t_stats['max_ms']:7.2f}ms")

        results.append({
            "scenario": sc.name,
            "retrieval": ret,
            "pack_build": pack,
            "pso_update": pso,
            "tool_ingestion": t_stats,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Latency Benchmark")
    parser.add_argument("--scenario", type=str, help="Scenario name")
    parser.add_argument("--all", action="store_true", help="Run on all scenarios")
    args = parser.parse_args()

    scenario = None
    if args.scenario:
        scenarios = load_all_scenarios()
        scenario = next((s for s in scenarios if s.name == args.scenario), None)
        if not scenario:
            print(f"Scenario '{args.scenario}' not found.")
            sys.exit(1)

    run_benchmark(scenario=scenario, all_scenarios=args.all)

    print(f"\n{'='*70}")
    print("Benchmark complete.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
