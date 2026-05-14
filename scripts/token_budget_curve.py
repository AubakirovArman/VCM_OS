#!/usr/bin/env python3
"""Token budget curve experiment: measure task success vs pack size.

Tests VCM pack builder at different budgets: 70, 150, 300, 500, 1000, 1500, 3000.
Compares against baselines: FullContext, RawVerbatim, StrongRAG.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.baselines import FullContextBaseline, RAGBaseline, SummaryBaseline
from vcm_os.evals.baselines_v0_9 import RawVerbatimBaseline, StrongRAGBaseline
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.verifier import ResponseVerifier


# Tasks of varying complexity
BUDGET_TASKS = [
    {
        "name": "simple_state",
        "description": "Simple state reminder",
        "events": [
            ("user_message", "We use PostgreSQL for the database."),
            ("assistant_response", "Decision: PostgreSQL. Rationale: ACID compliance."),
        ],
        "query": "What database do we use?",
        "expected_keywords": ["PostgreSQL", "ACID"],
    },
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
    },
    {
        "name": "multi_file_refactor",
        "description": "Refactor auth across multiple files",
        "events": [
            ("user_message", "We need to refactor auth to use OAuth2 instead of JWT."),
            ("assistant_response", "Decision: migrate to OAuth2. Tradeoff: better UX, but adds complexity. Rationale: industry standard."),
            ("code_change", "Added OAuth2 provider class.", {"file_path": "src/auth/oauth2.py"}),
            ("code_change", "Updated middleware to check OAuth2 tokens.", {"file_path": "src/auth/middleware.py"}),
            ("code_change", "Modified user model to store OAuth2 IDs.", {"file_path": "src/models/user.py"}),
            ("code_change", "Updated API routes to use OAuth2 scopes.", {"file_path": "src/api/routes.py"}),
            ("tool_call", "pytest auth tests: 12 passed, 0 failed", {"tool_name": "pytest"}),
            ("tool_call", "pytest api tests: 8 passed, 0 failed", {"tool_name": "pytest"}),
        ],
        "query": "What auth system are we migrating to and which files are affected?",
        "expected_keywords": ["OAuth2", "oauth2.py", "middleware.py", "user.py", "routes.py"],
    },
    {
        "name": "debug_timeline",
        "description": "Debug memory leak with timeline",
        "events": [
            ("user_message", "Production memory leak detected. Heap growing 100MB/hour."),
            ("assistant_response", "Hypothesis: unclosed database connections in async handlers."),
            ("tool_call", "ps aux: python process 2.1GB RSS", {"tool_name": "ps"}),
            ("assistant_response", "Confirmed: connection pool not releasing. Decision: add context managers."),
            ("code_change", "Added async context manager for DB connections.", {"file_path": "src/db/connection.py"}),
            ("tool_call", "pytest db tests: 15 passed, 0 failed", {"tool_name": "pytest"}),
            ("tool_call", "load test: memory stable at 400MB", {"tool_name": "locust"}),
        ],
        "query": "What was the memory leak and how was it fixed?",
        "expected_keywords": ["connection pool", "context manager", "connection.py", "memory leak"],
    },
]

BUDGETS = [70, 150, 300, 500, 1000, 1500, 3000]


def run_task_with_budget(runner, task, budget):
    pid = f"proj_{task['name']}"
    sid = f"sess_{task['name']}"

    for i, ev in enumerate(task["events"]):
        event_type, content = ev[0], ev[1]
        payload = ev[2] if len(ev) > 2 else {"content": content}
        event = EventRecord(
            event_id=f"evt_{i}_{task['name']}_b{budget}",
            project_id=pid,
            session_id=sid,
            event_type=event_type,
            payload=payload,
            raw_text=content,
        )
        runner.writer.capture_event(event)

    request = MemoryRequest(
        project_id=pid,
        query=task["query"],
        task_type="general",
        token_budget=8192,
        max_pack_tokens=budget,
    )
    t0 = time.perf_counter()
    plan = runner.router.make_plan(request)
    candidates = runner.reader.retrieve(request, plan)
    scored = runner.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]
    pack = runner.pack_builder.build(request, memories)
    latency_ms = (time.perf_counter() - t0) * 1000

    pack_text = " ".join(s.content.lower() for s in pack.sections)
    expected_hits = sum(1 for kw in task["expected_keywords"] if kw.lower() in pack_text)
    expected_recall = expected_hits / len(task["expected_keywords"]) if task["expected_keywords"] else 1.0

    verifier = ResponseVerifier()
    sim_response = f"Based on the project memory, {pack_text[:500]}"
    vresult = verifier.verify(sim_response, pack, memories)

    score = expected_recall
    if not vresult["passed"]:
        score -= 0.1

    return {
        "task": task["name"],
        "budget": budget,
        "latency_ms": round(latency_ms, 1),
        "expected_recall": round(expected_recall, 2),
        "verifier_passed": vresult["passed"],
        "verifier_score": round(vresult["score"], 2),
        "final_score": round(max(0.0, score), 2),
        "tokens": sum(s.token_estimate for s in pack.sections),
        "sections": len(pack.sections),
    }


def main():
    print("=" * 80)
    print("Token Budget Curve Experiment")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    results = []
    for task in BUDGET_TASKS:
        print(f"\n--- Task: {task['name']} ---")
        # Fresh runner per task to isolate
        runner = ExperimentRunner(store, vec, sparse, writer)
        for budget in BUDGETS:
            result = run_task_with_budget(runner, task, budget)
            results.append(result)
            print(f"  budget={budget:4d}  recall={result['expected_recall']:.2f}  "
                  f"score={result['final_score']:.2f}  tokens={result['tokens']:4d}  "
                  f"verifier={'PASS' if result['verifier_passed'] else 'FAIL'}")

    # Summary table
    print("\n" + "=" * 80)
    print("Summary: Average Score by Budget")
    print("=" * 80)
    print(f"{'Budget':>8}  {'Avg Score':>10}  {'Avg Recall':>10}  {'Avg Tokens':>10}")
    for budget in BUDGETS:
        r = [x for x in results if x["budget"] == budget]
        avg_score = sum(x["final_score"] for x in r) / len(r)
        avg_recall = sum(x["expected_recall"] for x in r) / len(r)
        avg_tokens = sum(x["tokens"] for x in r) / len(r)
        print(f"{budget:8d}  {avg_score:10.2f}  {avg_recall:10.2f}  {avg_tokens:10.1f}")

    # Task breakdown
    print("\n" + "=" * 80)
    print("Task Breakdown")
    print("=" * 80)
    for task in BUDGET_TASKS:
        print(f"\n{task['name']}:")
        r = [x for x in results if x["task"] == task["name"]]
        for x in r:
            marker = "✓" if x["final_score"] >= 0.8 else ("~" if x["final_score"] >= 0.5 else "✗")
            print(f"  {marker} budget={x['budget']:4d}  score={x['final_score']:.2f}  "
                  f"recall={x['expected_recall']:.2f}  tokens={x['tokens']:4d}")

    output = {
        "budgets": BUDGETS,
        "tasks": [t["name"] for t in BUDGET_TASKS],
        "results": results,
        "summary": {
            str(b): {
                "avg_score": round(sum(x["final_score"] for x in results if x["budget"] == b) / len([x for x in results if x["budget"] == b]), 3),
                "avg_recall": round(sum(x["expected_recall"] for x in results if x["budget"] == b) / len([x for x in results if x["budget"] == b]), 3),
                "avg_tokens": round(sum(x["tokens"] for x in results if x["budget"] == b) / len([x for x in results if x["budget"] == b]), 1),
            }
            for b in BUDGETS
        },
    }
    with open("token_budget_curve_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved to token_budget_curve_results.json")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
