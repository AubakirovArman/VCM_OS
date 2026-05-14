#!/usr/bin/env python3
"""Large-scale load tests for VCM-OS — 10k to 100k memories."""
import argparse
import json
import random
import string
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.health.dashboard import MemoryHealthDashboard
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt "
    "ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud exercitation ullamco "
    "laboris nisi ut aliquip ex ea commodo consequat duis aute irure dolor in reprehenderit "
    "in voluptate velit esse cillum dolore eu fugiat nulla pariatur excepteur sint occaecat"
).split()

TOPICS = [
    "auth", "cache", "database", "api", "frontend", "backend", "deployment",
    "testing", "security", "performance", "logging", "monitoring", "ci",
    "docker", "kubernetes", "terraform", "migration", "refactor", "bugfix",
]


def _random_text(length: int = 30) -> str:
    words = [random.choice(LOREM) for _ in range(length)]
    # Inject topic words for better semantic diversity
    for _ in range(3):
        words[random.randint(0, len(words) - 1)] = random.choice(TOPICS)
    return " ".join(words)


def _random_id(prefix: str, n: int = 8) -> str:
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=n))}"


def run_large_ingestion(store, writer, n_memories: int, n_projects: int):
    print(f"\n--- Large Ingestion: {n_memories} memories, {n_projects} projects ---")
    projects = [_random_id("proj") for _ in range(n_projects)]
    start = time.perf_counter()
    batch_size = 100
    batch = []

    for i in range(n_memories):
        pid = random.choice(projects)
        sid = _random_id("sess")
        event = EventRecord(
            event_id=_random_id("evt"),
            project_id=pid,
            session_id=sid,
            event_type=random.choice(["user_message", "assistant_response", "tool_call", "code_change"]),
            payload={"content": _random_text(20), "tool_name": random.choice(["pytest", "git", "deploy"])},
            raw_text=_random_text(20),
        )
        batch.append(event)

        if len(batch) >= batch_size:
            for ev in batch:
                writer.capture_event(ev)
            batch = []

        if (i + 1) % 1000 == 0:
            elapsed = time.perf_counter() - start
            print(f"  {i+1}/{n_memories} ingested, {elapsed:.1f}s ({(i+1)/elapsed:.1f} mem/s)")

    # Flush remaining
    for ev in batch:
        writer.capture_event(ev)

    total = time.perf_counter() - start
    rate = n_memories / total
    print(f"Total ingestion: {total:.1f}s ({rate:.1f} mem/s)")
    return total, rate


def run_query_latency(runner, n_queries: int):
    print(f"\n--- Query Latency: {n_queries} queries ---")
    with runner.store._conn() as conn:
        projects = [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM memory_objects LIMIT 10").fetchall()]
    if not projects:
        print("No projects found")
        return 0

    queries = ["What is the state?", "What decisions were made?", "What errors occurred?",
               "Show recent changes", "What is the status?", "Any blockers?"]
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
            print(f"  {i+1}/{n_queries} queries, avg {sum(latencies)/len(latencies)*1000:.1f}ms")

    if not latencies:
        return 0
    avg_ms = sum(latencies) / len(latencies) * 1000
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] * 1000
    print(f"Avg latency: {avg_ms:.1f}ms, P95: {p95_ms:.1f}ms")
    return avg_ms


def run_health_snapshot(store):
    print(f"\n--- Health Dashboard ---")
    dashboard = MemoryHealthDashboard(store)
    t0 = time.perf_counter()
    snap = dashboard.snapshot()
    t1 = time.perf_counter()
    print(f"Snapshot: {(t1-t0)*1000:.1f}ms")
    print(f"  Score: {snap['score']}")
    print(f"  Memories: {snap['basic']['memories']}")
    print(f"  Orphans: {snap['orphans']['ratio']*100:.1f}%")
    return snap


def main():
    parser = argparse.ArgumentParser(description="VCM OS Large-Scale Load Tests")
    parser.add_argument("--memories", type=int, default=10000, help="Number of memories")
    parser.add_argument("--projects", type=int, default=50, help="Number of projects")
    parser.add_argument("--queries", type=int, default=50, help="Number of queries")
    parser.add_argument("--output", type=str, default="load_test_large_results.json")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    print("=" * 70)
    print(f"VCM OS Large-Scale Load Test — {args.memories} memories")
    print("=" * 70)

    ingest_time, ingest_rate = run_large_ingestion(store, writer, args.memories, args.projects)
    query_ms = run_query_latency(runner, args.queries)
    snap = run_health_snapshot(store)

    results = {
        "config": {"memories": args.memories, "projects": args.projects, "queries": args.queries},
        "ingestion_time_sec": round(ingest_time, 1),
        "ingestion_rate_mem_per_sec": round(ingest_rate, 1),
        "query_avg_ms": round(query_ms, 1),
        "health_score": snap["score"],
        "total_memories": snap["basic"]["memories"],
        "total_projects": snap["basic"]["projects"],
        "orphan_ratio": snap["orphans"]["ratio"],
        "db_size_mb": round(snap["basic"].get("db_size_bytes", 0) / (1024 * 1024), 1),
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
