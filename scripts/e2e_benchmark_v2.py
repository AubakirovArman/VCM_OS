#!/usr/bin/env python3
"""End-to-end coding task benchmark v2 — 30 tasks across 10 categories."""
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


def _ev(event_type, content, **kwargs):
    return (event_type, content, kwargs)


E2E_TASKS = [
    # === AUTH (3) ===
    {
        "name": "auth_jwt",
        "category": "auth",
        "events": [
            _ev("user_message", "Add JWT authentication to the API."),
            _ev("assistant_response", "Decision: use PyJWT with middleware. Rationale: standard, well-maintained."),
            _ev("code_change", "Added JWT middleware class.", file_path="src/auth/jwt_middleware.py"),
            _ev("tool_call", "pytest auth tests: 5 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "How is JWT authentication implemented?",
        "expected_keywords": ["PyJWT", "middleware", "jwt_middleware.py"],
    },
    {
        "name": "auth_oauth2",
        "category": "auth",
        "events": [
            _ev("user_message", "Users want to login with Google. Add OAuth2."),
            _ev("assistant_response", "Decision: use OAuth2 with PKCE. Tradeoff: better UX, adds complexity."),
            _ev("code_change", "Added OAuth2 provider handler.", file_path="src/auth/oauth2.py"),
            _ev("code_change", "Updated login flow to redirect to Google.", file_path="src/auth/login.py"),
            _ev("tool_call", "pytest auth tests: 8 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What auth system do we use for third-party login?",
        "expected_keywords": ["OAuth2", "oauth2.py", "login.py", "Google"],
    },
    {
        "name": "auth_rbac",
        "category": "auth",
        "events": [
            _ev("user_message", "We need role-based access control. Admin, editor, viewer."),
            _ev("assistant_response", "Decision: RBAC with three roles. Admin can do everything."),
            _ev("code_change", "Added Role enum and permission checks.", file_path="src/auth/rbac.py"),
            _ev("tool_call", "pytest rbac tests: 6 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What roles do we have and how is RBAC implemented?",
        "expected_keywords": ["RBAC", "rbac.py", "Admin", "editor", "viewer"],
    },
    # === CACHE (3) ===
    {
        "name": "cache_redis",
        "category": "cache",
        "events": [
            _ev("user_message", "Add Redis caching for API responses."),
            _ev("assistant_response", "Decision: Redis with 5min TTL. Rationale: fast, widely used."),
            _ev("code_change", "Added Redis cache wrapper.", file_path="src/cache/redis.py"),
            _ev("tool_call", "pytest cache tests: 4 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "How is API caching implemented?",
        "expected_keywords": ["Redis", "redis.py", "TTL"],
    },
    {
        "name": "cache_migration_memcached",
        "category": "cache",
        "events": [
            _ev("user_message", "Redis is using too much memory. Switch to Memcached."),
            _ev("assistant_response", "Decision: migrate to Memcached. Tradeoff: simpler, better memory efficiency."),
            _ev("code_change", "Replaced Redis client with Memcached client.", file_path="src/cache/memcached.py"),
            _ev("tool_call", "pytest cache tests: 8 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What caching system are we using?",
        "expected_keywords": ["Memcached", "memcached.py", "migrate"],
    },
    {
        "name": "cache_cdn",
        "category": "cache",
        "events": [
            _ev("user_message", "Static assets load slowly. Add a CDN."),
            _ev("assistant_response", "Decision: CloudFront CDN for static assets. Rationale: global edge locations."),
            _ev("code_change", "Updated asset URLs to use CDN.", file_path="src/static/cdn_config.py"),
            _ev("tool_call", "Lighthouse score improved from 45 to 92", tool_name="lighthouse"),
        ],
        "query": "How do we serve static assets?",
        "expected_keywords": ["CDN", "CloudFront", "cdn_config.py", "static"],
    },
    # === DATABASE (3) ===
    {
        "name": "db_postgres",
        "category": "database",
        "events": [
            _ev("user_message", "Set up PostgreSQL for the project."),
            _ev("assistant_response", "Decision: PostgreSQL 15. Rationale: ACID, JSON support, mature."),
            _ev("code_change", "Added SQLAlchemy models and connection pool.", file_path="src/db/models.py"),
            _ev("tool_call", "pytest db tests: 10 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What database do we use and why?",
        "expected_keywords": ["PostgreSQL", "models.py", "ACID"],
    },
    {
        "name": "db_migration",
        "category": "database",
        "events": [
            _ev("user_message", "We need to add a users table with email unique constraint."),
            _ev("assistant_response", "Decision: Alembic migration for users table."),
            _ev("code_change", "Added migration creating users table.", file_path="migrations/001_add_users.py"),
            _ev("tool_call", "alembic upgrade head: OK", tool_name="alembic"),
        ],
        "query": "How was the users table created?",
        "expected_keywords": ["Alembic", "users", "migration", "001_add_users.py"],
    },
    {
        "name": "db_indexing",
        "category": "database",
        "events": [
            _ev("user_message", "Queries on created_at are slow. Add an index."),
            _ev("assistant_response", "Decision: B-tree index on created_at. Rationale: range queries."),
            _ev("code_change", "Added index on created_at column.", file_path="migrations/002_add_index.py"),
            _ev("tool_call", "EXPLAIN ANALYZE: execution time 12ms → 0.3ms", tool_name="psql"),
        ],
        "query": "How did we fix the slow queries?",
        "expected_keywords": ["index", "created_at", "B-tree", "002_add_index.py"],
    },
    # === API (3) ===
    {
        "name": "api_rest",
        "category": "api",
        "events": [
            _ev("user_message", "Build REST API for user CRUD."),
            _ev("assistant_response", "Decision: FastAPI with Pydantic models. Rationale: type safety, auto-docs."),
            _ev("code_change", "Added REST endpoints for user CRUD.", file_path="src/api/users.py"),
            _ev("tool_call", "pytest api tests: 12 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "How is the user API implemented?",
        "expected_keywords": ["REST", "FastAPI", "users.py", "CRUD"],
    },
    {
        "name": "api_graphql",
        "category": "api",
        "events": [
            _ev("user_message", "Add GraphQL for complex queries."),
            _ev("assistant_response", "Decision: Strawberry GraphQL. Rationale: python-native, type-safe."),
            _ev("code_change", "Added GraphQL schema and resolvers.", file_path="src/api/graphql.py"),
            _ev("tool_call", "pytest graphql tests: 6 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What GraphQL library do we use?",
        "expected_keywords": ["GraphQL", "Strawberry", "graphql.py"],
    },
    {
        "name": "api_versioning",
        "category": "api",
        "events": [
            _ev("user_message", "We need API versioning for backward compatibility."),
            _ev("assistant_response", "Decision: URL versioning /v1/ /v2/. Rationale: explicit, cache-friendly."),
            _ev("code_change", "Added version prefix to API routes.", file_path="src/api/versioning.py"),
            _ev("tool_call", "Integration tests pass for v1 and v2", tool_name="pytest"),
        ],
        "query": "How do we version the API?",
        "expected_keywords": ["versioning", "/v1/", "/v2/", "versioning.py"],
    },
    # === TESTING (3) ===
    {
        "name": "test_unit",
        "category": "testing",
        "events": [
            _ev("user_message", "Set up unit testing with pytest."),
            _ev("assistant_response", "Decision: pytest with fixtures and parametrize."),
            _ev("code_change", "Added pytest config and test utilities.", file_path="tests/conftest.py"),
            _ev("tool_call", "pytest unit: 45 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "What testing framework do we use?",
        "expected_keywords": ["pytest", "conftest.py", "unit"],
    },
    {
        "name": "test_integration",
        "category": "testing",
        "events": [
            _ev("user_message", "Add integration tests for the database layer."),
            _ev("assistant_response", "Decision: pytest with testcontainers for PostgreSQL."),
            _ev("code_change", "Added integration test base with Docker DB.", file_path="tests/integration/test_db.py"),
            _ev("tool_call", "pytest integration: 8 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "How do we run integration tests?",
        "expected_keywords": ["integration", "testcontainers", "test_db.py", "PostgreSQL"],
    },
    {
        "name": "test_e2e",
        "category": "testing",
        "events": [
            _ev("user_message", "Add end-to-end tests for the login flow."),
            _ev("assistant_response", "Decision: Playwright for browser automation."),
            _ev("code_change", "Added Playwright E2E tests for login.", file_path="tests/e2e/test_login.py"),
            _ev("tool_call", "playwright test: 3 passed, 0 failed", tool_name="playwright"),
        ],
        "query": "What tool do we use for E2E testing?",
        "expected_keywords": ["Playwright", "e2e", "test_login.py"],
    },
    # === DEPLOYMENT (3) ===
    {
        "name": "deploy_docker",
        "category": "deployment",
        "events": [
            _ev("user_message", "Containerize the application with Docker."),
            _ev("assistant_response", "Decision: multi-stage Dockerfile with distroless final image."),
            _ev("code_change", "Added Dockerfile and docker-compose.yml.", file_path="Dockerfile"),
            _ev("tool_call", "docker build: success, image 124MB", tool_name="docker"),
        ],
        "query": "How is the app containerized?",
        "expected_keywords": ["Docker", "Dockerfile", "distroless", "docker-compose"],
    },
    {
        "name": "deploy_k8s",
        "category": "deployment",
        "events": [
            _ev("user_message", "Deploy to Kubernetes with auto-scaling."),
            _ev("assistant_response", "Decision: HPA with 2-10 replicas based on CPU."),
            _ev("code_change", "Added deployment manifest with HPA.", file_path="k8s/deployment.yaml"),
            _ev("tool_call", "kubectl apply: deployment created", tool_name="kubectl"),
        ],
        "query": "How do we handle scaling in Kubernetes?",
        "expected_keywords": ["Kubernetes", "HPA", "deployment.yaml", "auto-scaling"],
    },
    {
        "name": "deploy_ci",
        "category": "deployment",
        "events": [
            _ev("user_message", "Set up CI/CD pipeline."),
            _ev("assistant_response", "Decision: GitHub Actions with matrix testing."),
            _ev("code_change", "Added GitHub Actions workflow.", file_path=".github/workflows/ci.yml"),
            _ev("tool_call", "CI pipeline: test, lint, build, deploy — all green", tool_name="github_actions"),
        ],
        "query": "What CI/CD system do we use?",
        "expected_keywords": ["GitHub Actions", "ci.yml", "CI/CD"],
    },
    # === ERROR HANDLING (3) ===
    {
        "name": "error_exceptions",
        "category": "error_handling",
        "events": [
            _ev("user_message", "Unify exception handling across the API."),
            _ev("assistant_response", "Decision: custom AppException with HTTP status mapping."),
            _ev("code_change", "Added exception hierarchy and handlers.", file_path="src/errors/exceptions.py"),
            _ev("tool_call", "pytest error tests: 5 passed, 0 failed", tool_name="pytest"),
        ],
        "query": "How do we handle API errors?",
        "expected_keywords": ["AppException", "exceptions.py", "HTTP status"],
    },
    {
        "name": "error_logging",
        "category": "error_handling",
        "events": [
            _ev("user_message", "Add structured logging with correlation IDs."),
            _ev("assistant_response", "Decision: structlog with JSON output and correlation_id middleware."),
            _ev("code_change", "Added structured logging setup.", file_path="src/logging/config.py"),
            _ev("tool_call", "Logs verified: JSON format with request_id", tool_name="manual"),
        ],
        "query": "How is logging structured?",
        "expected_keywords": ["structlog", "JSON", "correlation_id", "config.py"],
    },
    {
        "name": "error_retries",
        "category": "error_handling",
        "events": [
            _ev("user_message", "Add retry logic for external API calls."),
            _ev("assistant_response", "Decision: tenacity with exponential backoff, max 3 retries."),
            _ev("code_change", "Added retry decorator for HTTP clients.", file_path="src/http/retry.py"),
            _ev("tool_call", "Tests pass: transient failures recovered", tool_name="pytest"),
        ],
        "query": "How do we handle transient external API failures?",
        "expected_keywords": ["tenacity", "retry", "backoff", "retry.py"],
    },
    # === REFACTORING (3) ===
    {
        "name": "refactor_cleanup",
        "category": "refactoring",
        "events": [
            _ev("user_message", "Clean up dead code and unused imports."),
            _ev("assistant_response", "Decision: ruff check + autofix, remove 3 unused modules."),
            _ev("code_change", "Removed dead code and fixed imports.", file_path="src/"),
            _ev("tool_call", "ruff check: 0 errors, 0 warnings", tool_name="ruff"),
        ],
        "query": "How did we clean up the codebase?",
        "expected_keywords": ["ruff", "dead code", "imports"],
    },
    {
        "name": "refactor_performance",
        "category": "refactoring",
        "events": [
            _ev("user_message", "Optimize the hot path in user lookup."),
            _ev("assistant_response", "Decision: add selectinload for relationships, reduce N+1 queries."),
            _ev("code_change", "Optimized user query with eager loading.", file_path="src/db/queries.py"),
            _ev("tool_call", "Benchmark: 120ms → 8ms per request", tool_name="pytest-benchmark"),
        ],
        "query": "How was user lookup performance improved?",
        "expected_keywords": ["selectinload", "N+1", "queries.py", "eager loading"],
    },
    {
        "name": "refactor_dedup",
        "category": "refactoring",
        "events": [
            _ev("user_message", "Deduplicate validation logic across modules."),
            _ev("assistant_response", "Decision: extract shared validators to validators.py."),
            _ev("code_change", "Extracted and unified validation logic.", file_path="src/validators.py"),
            _ev("tool_call", "Coverage: +12% after deduplication", tool_name="coverage"),
        ],
        "query": "How did we deduplicate validation?",
        "expected_keywords": ["validators.py", "deduplicate", "validation"],
    },
    # === ARCHITECTURE (3) ===
    {
        "name": "arch_microservices",
        "category": "architecture",
        "events": [
            _ev("user_message", "Split monolith into microservices."),
            _ev("assistant_response", "Decision: extract auth and billing into separate services. Use gRPC internally."),
            _ev("code_change", "Created auth-service and billing-service.", file_path="services/"),
            _ev("tool_call", "Integration tests pass across services", tool_name="pytest"),
        ],
        "query": "What services did we extract from the monolith?",
        "expected_keywords": ["microservices", "auth-service", "billing-service", "gRPC"],
    },
    {
        "name": "arch_event_driven",
        "category": "architecture",
        "events": [
            _ev("user_message", "Make order processing asynchronous with events."),
            _ev("assistant_response", "Decision: RabbitMQ for order events. Separate producer and consumer."),
            _ev("code_change", "Added event publisher and consumer for orders.", file_path="src/events/order_events.py"),
            _ev("tool_call", "E2E test: order placed → email sent in <2s", tool_name="pytest"),
        ],
        "query": "How do we handle order processing asynchronously?",
        "expected_keywords": ["RabbitMQ", "event-driven", "order_events.py", "async"],
    },
    {
        "name": "arch_cqrs",
        "category": "architecture",
        "events": [
            _ev("user_message", "Separate read and write models for analytics."),
            _ev("assistant_response", "Decision: CQRS with read replicas for analytics queries."),
            _ev("code_change", "Added read model and query handlers.", file_path="src/analytics/read_model.py"),
            _ev("tool_call", "Analytics dashboard loads in 200ms", tool_name="manual"),
        ],
        "query": "How do we handle analytics reads?",
        "expected_keywords": ["CQRS", "read_model.py", "analytics", "read replicas"],
    },
    # === DEBUGGING (3) ===
    {
        "name": "debug_memory_leak",
        "category": "debugging",
        "events": [
            _ev("user_message", "Production memory leak: heap growing 100MB/hour."),
            _ev("assistant_response", "Hypothesis: unclosed DB connections in async handlers."),
            _ev("tool_call", "ps aux: python 2.1GB RSS", tool_name="ps"),
            _ev("assistant_response", "Confirmed: connection pool not releasing. Fix: context managers."),
            _ev("code_change", "Added async context manager for DB connections.", file_path="src/db/connection.py"),
            _ev("tool_call", "Load test: memory stable at 400MB", tool_name="locust"),
        ],
        "query": "What caused the memory leak and how was it fixed?",
        "expected_keywords": ["connection pool", "context manager", "connection.py", "memory leak"],
    },
    {
        "name": "debug_race_condition",
        "category": "debugging",
        "events": [
            _ev("user_message", "Intermittent test failure: duplicate order IDs."),
            _ev("assistant_response", "Hypothesis: race condition in ID generation under concurrent load."),
            _ev("code_change", "Replaced incrementing counter with UUID7.", file_path="src/models/order.py"),
            _ev("tool_call", "Stress test: 0 duplicates in 100k orders", tool_name="pytest"),
        ],
        "query": "How was the duplicate order ID race condition fixed?",
        "expected_keywords": ["race condition", "UUID7", "order.py", "concurrent"],
    },
    {
        "name": "debug_timeout",
        "category": "debugging",
        "events": [
            _ev("user_message", "Payment API calls timeout randomly."),
            _ev("assistant_response", "Root cause: no timeout set on httpx client. Default waits forever."),
            _ev("code_change", "Added 10s timeout to all external HTTP calls.", file_path="src/http/client.py"),
            _ev("tool_call", "No timeouts in 24h production monitoring", tool_name="prometheus"),
        ],
        "query": "Why were payment API calls timing out?",
        "expected_keywords": ["timeout", "httpx", "client.py", "10s"],
    },
]


def run_e2e_task(runner, task):
    pid = f"proj_e2e_{task['name']}"
    sid = f"sess_e2e_{task['name']}"

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

    pack_text = " ".join(s.content.lower() for s in pack.sections)
    expected_hits = sum(1 for kw in task["expected_keywords"] if kw.lower() in pack_text)
    expected_recall = expected_hits / len(task["expected_keywords"]) if task["expected_keywords"] else 1.0

    verifier = ResponseVerifier()
    sim_response = f"Based on the project memory, {pack_text[:500]}"
    vresult = verifier.verify(sim_response, pack, memories)

    score = max(0.0, expected_recall)
    if not vresult["passed"]:
        score -= 0.1

    return {
        "task": task["name"],
        "category": task["category"],
        "latency_ms": round(latency_ms, 1),
        "expected_recall": round(expected_recall, 2),
        "verifier_passed": vresult["passed"],
        "verifier_score": round(vresult["score"], 2),
        "final_score": round(score, 2),
        "tokens": sum(s.token_estimate for s in pack.sections),
    }


def main():
    print("=" * 80)
    print("VCM-OS End-to-End Coding Task Benchmark v2")
    print(f"Tasks: {len(E2E_TASKS)} across 10 categories")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    results = []
    for task in E2E_TASKS:
        runner = ExperimentRunner(store, vec, sparse, writer)
        result = run_e2e_task(runner, task)
        results.append(result)

    # Per-category summary
    category_scores = {}
    for r in results:
        cat = r["category"]
        if cat not in category_scores:
            category_scores[cat] = []
        category_scores[cat].append(r["final_score"])

    print("\n" + "=" * 80)
    print("Results by Category")
    print("=" * 80)
    for cat, scores in sorted(category_scores.items()):
        avg = sum(scores) / len(scores)
        passed = sum(1 for s in scores if s >= 0.8)
        print(f"  {cat:20s}  avg={avg:.2f}  pass={passed}/{len(scores)}")

    # Overall summary
    avg_score = sum(r["final_score"] for r in results) / len(results)
    avg_recall = sum(r["expected_recall"] for r in results) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    passed_count = sum(1 for r in results if r["final_score"] >= 0.8)

    print("\n" + "=" * 80)
    print("Overall Summary")
    print("=" * 80)
    print(f"Tasks: {len(results)}")
    print(f"Passed (≥0.8): {passed_count}/{len(results)}")
    print(f"Avg Score: {avg_score:.2f}")
    print(f"Avg Recall: {avg_recall:.2f}")
    print(f"Avg Latency: {avg_latency:.1f}ms")

    # Task detail
    print("\n" + "=" * 80)
    print("Task Details")
    print("=" * 80)
    for r in results:
        marker = "✓" if r["final_score"] >= 0.8 else ("~" if r["final_score"] >= 0.5 else "✗")
        print(f"{marker} {r['task']:30s} score={r['final_score']:.2f} recall={r['expected_recall']:.2f} "
              f"tokens={r['tokens']:4d} verifier={'PASS' if r['verifier_passed'] else 'FAIL'}")

    output = {
        "tasks": results,
        "category_summary": {cat: {"avg": round(sum(scores)/len(scores), 3), "count": len(scores)} for cat, scores in category_scores.items()},
        "overall": {
            "avg_score": round(avg_score, 3),
            "avg_recall": round(avg_recall, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "passed": passed_count,
            "total": len(results),
        },
    }
    with open("e2e_benchmark_v2_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved to e2e_benchmark_v2_results.json")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
