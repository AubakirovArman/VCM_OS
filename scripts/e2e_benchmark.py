#!/usr/bin/env python3
"""End-to-end coding task benchmark for VCM-OS."""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.verifier import ResponseVerifier


# Simulated coding tasks
E2E_TASKS = [
    {
        "name": "auth_middleware",
        "description": "Add JWT auth middleware to API",
        "events": [
            ("user_message", "We need to add JWT authentication to the API. Use PyJWT library."),
            ("assistant_response", "Decision: use PyJWT with middleware pattern. Rationale: standard, well-maintained."),
            ("code_change", "Added JWT middleware class.", {"file_path": "src/auth/jwt_middleware.py"}),
            ("tool_call", "pytest auth tests: 5 passed, 0 failed", {"tool_name": "pytest"}),
        ],
        "query": "How is JWT authentication implemented?",
        "expected_keywords": ["PyJWT", "middleware", "jwt_middleware.py"],
        "forbidden_keywords": [],
    },
    {
        "name": "cache_migration",
        "description": "Migrate from Redis to Memcached",
        "events": [
            ("user_message", "Redis is using too much memory. We should switch to Memcached."),
            ("assistant_response", "Decision: migrate to Memcached. Tradeoff: simpler data model, better memory efficiency."),
            ("code_change", "Replaced Redis client with Memcached client.", {"file_path": "src/cache/memcached.py"}),
            ("tool_call", "pytest cache tests: 8 passed, 0 failed", {"tool_name": "pytest"}),
        ],
        "query": "What caching system are we using?",
        "expected_keywords": ["Memcached", "memcached.py", "migrate"],
        "forbidden_keywords": [],  # Historical mentions of Redis are OK in pack
    },
    {
        "name": "error_handling",
        "description": "Fix database connection error",
        "events": [
            ("user_message", "Production error: database connection pool exhausted."),
            ("assistant_response", "Root cause: connection pool size too small. Fix: increase pool size to 20."),
            ("code_change", "Increased connection pool size.", {"file_path": "src/db/pool.py"}),
            ("tool_call", "pytest db tests: 10 passed, 0 failed", {"tool_name": "pytest"}),
        ],
        "query": "What caused the database connection issue and how was it fixed?",
        "expected_keywords": ["connection pool", "exhausted", "pool.py"],
        "forbidden_keywords": [],
    },
]


def run_e2e_task(runner, task):
    """Run a single end-to-end task and score it."""
    pid = f"proj_e2e_{task['name']}"
    sid = f"sess_e2e_{task['name']}"

    # Ingest events
    for i, ev in enumerate(task["events"]):
        event_type, content = ev[0], ev[1]
        payload = ev[2] if len(ev) > 2 else {"content": content}
        event = EventRecord(
            event_id=f"evt_{i}_{task['name']}",
            project_id=pid,
            session_id=sid,
            event_type=event_type,
            payload=payload,
            raw_text=content,
        )
        runner.writer.capture_event(event)

    # Build pack
    request = MemoryRequest(
        project_id=pid,
        query=task["query"],
        task_type="general",
        token_budget=8192,
        max_pack_tokens=500,
    )
    t0 = time.perf_counter()
    plan = runner.router.make_plan(request)
    candidates = runner.reader.retrieve(request, plan)
    scored = runner.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]
    pack = runner.pack_builder.build(request, memories)
    latency_ms = (time.perf_counter() - t0) * 1000

    # Simulate LLM response (for benchmark, we just check pack content)
    pack_text = " ".join(s.content.lower() for s in pack.sections)

    # Check expected keywords
    expected_hits = sum(1 for kw in task["expected_keywords"] if kw.lower() in pack_text)
    expected_recall = expected_hits / len(task["expected_keywords"]) if task["expected_keywords"] else 1.0

    # Check forbidden keywords
    forbidden_hits = sum(1 for kw in task["forbidden_keywords"] if kw.lower() in pack_text)
    forbidden_penalty = forbidden_hits / len(task["forbidden_keywords"]) if task["forbidden_keywords"] else 0.0

    # Verifier check
    verifier = ResponseVerifier()
    sim_response = f"Based on the project memory, {pack_text[:500]}"
    vresult = verifier.verify(sim_response, pack, memories)

    score = max(0.0, expected_recall - forbidden_penalty * 0.5)
    if not vresult["passed"]:
        score -= 0.2

    return {
        "task": task["name"],
        "latency_ms": round(latency_ms, 1),
        "expected_recall": round(expected_recall, 2),
        "forbidden_penalty": round(forbidden_penalty, 2),
        "verifier_passed": vresult["passed"],
        "verifier_score": vresult["score"],
        "final_score": round(score, 2),
        "tokens": sum(s.token_estimate for s in pack.sections),
    }


def main():
    print("=" * 70)
    print("VCM-OS End-to-End Coding Task Benchmark")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    results = []
    for task in E2E_TASKS:
        print(f"\n--- Task: {task['name']} ---")
        result = run_e2e_task(runner, task)
        results.append(result)
        print(f"  Score: {result['final_score']}")
        print(f"  Expected recall: {result['expected_recall']}")
        print(f"  Verifier: {'PASS' if result['verifier_passed'] else 'FAIL'}")
        print(f"  Latency: {result['latency_ms']}ms")
        print(f"  Tokens: {result['tokens']}")

    avg_score = sum(r["final_score"] for r in results) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Tasks: {len(results)}")
    print(f"Avg Score: {avg_score:.2f}")
    print(f"Avg Latency: {avg_latency:.1f}ms")
    print(f"All verifier passed: {all(r['verifier_passed'] for r in results)}")

    output = {
        "tasks": results,
        "avg_score": round(avg_score, 2),
        "avg_latency_ms": round(avg_latency, 1),
    }
    with open("e2e_benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved to e2e_benchmark_results.json")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
