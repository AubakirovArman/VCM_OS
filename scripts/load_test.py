#!/usr/bin/env python3
"""Large-store load tests for VCM OS."""
import argparse
import random
import string
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryObject, MemoryType, SourceType
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua "
    "ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat "
    "duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur "
    "excepteur sint occaecat cupidatat non proident sunt in culpa qui officia deserunt mollit anim id est laborum"
).split()


def _random_text(length: int = 50) -> str:
    words = [random.choice(LOREM) for _ in range(length)]
    return " ".join(words)


def _random_id(prefix: str, n: int = 8) -> str:
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=n))}"


def run_ingestion_load(store, writer, n_memories: int, n_projects: int):
    print(f"\n--- Ingestion Load: {n_memories} memories across {n_projects} projects ---")
    projects = [_random_id("proj") for _ in range(n_projects)]
    start = time.perf_counter()
    for i in range(n_memories):
        pid = random.choice(projects)
        sid = _random_id("sess")
        event = EventRecord(
            event_id=_random_id("evt"),
            project_id=pid,
            session_id=sid,
            event_type=random.choice(["user_message", "assistant_response", "tool_call", "code_change"]),
            payload={"content": _random_text(30), "tool_name": random.choice(["pytest", "git", "deploy"])},
            raw_text=_random_text(30),
        )
        writer.capture_event(event)
        if (i + 1) % 100 == 0:
            elapsed = time.perf_counter() - start
            print(f"  {i+1}/{n_memories} ingested, {elapsed:.1f}s ({(i+1)/elapsed:.1f} mem/s)")
    total = time.perf_counter() - start
    print(f"Total ingestion: {total:.2f}s ({n_memories/total:.1f} mem/s)")
    return total


def run_query_latency(runner, n_queries: int):
    print(f"\n--- Query Latency: {n_queries} queries ---")
    with runner.store._conn() as conn:
        projects = [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM memory_objects LIMIT 10").fetchall()]
    if not projects:
        print("No projects found, skipping query latency test")
        return 0
    queries = ["What is the current state?", "What decisions were made?", "What errors occurred?", "Show me recent changes", "What is the status?"]
    latencies = []
    from vcm_os.evals.scenarios.synthetic_projects import EvalScenario
    for i in range(n_queries):
        pid = random.choice(projects)
        q = random.choice(queries)
        scenario = EvalScenario(
            name="load_test", project_id=pid, events=[],
            expected_goals=[], expected_decisions=[], expected_errors=[],
            test_query=q, expected_answer_keywords=[], protected_terms=[],
        )
        t0 = time.perf_counter()
        try:
            pack = runner.run_vcm(scenario, override_query=q)
        except Exception as e:
            print(f"  Query failed: {e}")
            continue
        t1 = time.perf_counter()
        latencies.append(t1 - t0)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{n_queries} queries, avg latency {sum(latencies)/len(latencies)*1000:.1f}ms")
    if not latencies:
        return 0
    avg_ms = sum(latencies) / len(latencies) * 1000
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] * 1000
    print(f"Avg latency: {avg_ms:.1f}ms, P95: {p95_ms:.1f}ms")
    return avg_ms


def run_pso_latency(store, n_projects: int):
    print(f"\n--- PSO Latency ---")
    from vcm_os.memory.project_state.store import ProjectStateStore
    pso_store = ProjectStateStore(store)
    with store._conn() as conn:
        projects = [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM memory_objects LIMIT ?", (n_projects,)).fetchall()]
    latencies = []
    for pid in projects:
        t0 = time.perf_counter()
        pso = pso_store.load(pid)
        t1 = time.perf_counter()
        latencies.append(t1 - t0)
    avg_ms = sum(latencies) / len(latencies) * 1000
    print(f"PSO load avg: {avg_ms:.1f}ms over {len(projects)} projects")
    return avg_ms


def run_health_snapshot(store):
    print(f"\n--- Health Dashboard Snapshot ---")
    from vcm_os.health.dashboard import MemoryHealthDashboard
    dashboard = MemoryHealthDashboard(store)
    t0 = time.perf_counter()
    snap = dashboard.snapshot()
    t1 = time.perf_counter()
    print(f"Snapshot computed in {(t1-t0)*1000:.1f}ms")
    print(f"  Score: {snap['score']}")
    print(f"  Memories: {snap['basic']['memories']}")
    print(f"  Events: {snap['basic']['events']}")
    print(f"  Projects: {snap['basic']['projects']}")
    print(f"  Avg age: {snap['ages']['avg_days']:.1f} days")
    print(f"  Orphans: {snap['orphans']['ratio']*100:.1f}%")
    return snap


def main():
    parser = argparse.ArgumentParser(description="VCM OS Load Tests")
    parser.add_argument("--memories", type=int, default=500, help="Number of memories to ingest")
    parser.add_argument("--projects", type=int, default=10, help="Number of projects")
    parser.add_argument("--queries", type=int, default=50, help="Number of queries to run")
    parser.add_argument("--output", type=str, default="load_test_results.json", help="Output JSON file")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    print("=" * 70)
    print("VCM OS Large-Store Load Tests")
    print("=" * 70)

    runner = ExperimentRunner(store, vec, sparse, writer)
    ingest_time = run_ingestion_load(store, writer, args.memories, args.projects)
    query_ms = run_query_latency(runner, args.queries)
    pso_ms = run_pso_latency(store, args.projects)
    snap = run_health_snapshot(store)

    results = {
        "config": {"memories": args.memories, "projects": args.projects, "queries": args.queries},
        "ingestion_time_sec": round(ingest_time, 2),
        "ingestion_rate_mem_per_sec": round(args.memories / ingest_time, 1) if ingest_time > 0 else 0,
        "query_avg_ms": round(query_ms, 2),
        "pso_avg_ms": round(pso_ms, 2),
        "health_score": snap["score"],
        "total_memories": snap["basic"]["memories"],
        "total_projects": snap["basic"]["projects"],
        "orphan_ratio": snap["orphans"]["ratio"],
    }

    import json
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
