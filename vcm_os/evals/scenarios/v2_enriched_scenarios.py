"""Enriched scenarios with full v2 Decision/Error/PSO fields."""
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario
from vcm_os.schemas import EventRecord


def _evt(project_id, session_id, event_type, content, payload=None):
    return EventRecord(
        project_id=project_id,
        session_id=session_id,
        event_type=event_type,
        payload=payload or {"content": content},
        raw_text=content,
    )


def v2_rich_decision_scenario() -> EvalScenario:
    """Decision with full v2 fields: rationale, alternatives, tradeoffs."""
    pid = "proj_v2_decision"
    sid = "sess_v2_001"
    events = [
        _evt(pid, sid, "user_message", (
            "We need to choose a database. "
            "Rationale: PostgreSQL offers better JSON support and ACID compliance for our use case. "
            "Alternative: MySQL — faster for simple reads, but weaker JSON support. "
            "Alternative: MongoDB — flexible schema, but no ACID transactions. "
            "Tradeoff: PostgreSQL is slower to set up but more robust long-term."
        )),
        _evt(pid, sid, "assistant_response", (
            "Decision: use PostgreSQL as primary database. "
            "Rationale: JSON support and ACID compliance align with project requirements. "
            "Alternative considered: MySQL, MongoDB. "
            "Tradeoff: higher setup cost, better long-term reliability."
        )),
        _evt(pid, sid, "code_change", "Added PostgreSQL connection pool.", {"file_path": "src/db/pool.py"}),
    ]
    return EvalScenario(
        name="v2_rich_decision",
        project_id=pid,
        events=events,
        expected_goals=["choose a database"],
        expected_decisions=["use PostgreSQL"],
        expected_errors=[],
        test_query="What database decision was made and why?",
        expected_answer_keywords=["PostgreSQL", "JSON support", "ACID", "MySQL", "MongoDB", "tradeoff"],
        protected_terms=["src/db/pool.py"],
    )


def v2_rich_error_scenario() -> EvalScenario:
    """Error with full v2 fields: root_cause, fix_attempt, verified_fix, affected_files, recurrence_risk."""
    pid = "proj_v2_error"
    sid = "sess_v2_002"
    events = [
        _evt(pid, sid, "user_message", (
            "Production alert: memory leak in cache layer. "
            "Root cause: LRU cache retains references to expired objects, preventing garbage collection. "
            "Affected files: src/cache/lru.py, src/cache/manager.py"
        )),
        _evt(pid, sid, "assistant_response", (
            "Fix attempt: replace LRU with TTL-based cache and add explicit cleanup on eviction. "
            "Verified fix: load test shows stable memory at 45% after 2 hours. "
            "Recurrence risk: medium — if TTL is misconfigured, leak may return."
        )),
        _evt(pid, sid, "code_change", "Replaced LRU with TTL cache.", {"file_path": "src/cache/ttl.py"}),
        _evt(pid, sid, "tool_call", "pytest cache tests: 15 passed, 0 failed", {"tool_name": "pytest"}),
    ]
    return EvalScenario(
        name="v2_rich_error",
        project_id=pid,
        events=events,
        expected_goals=["fix memory leak"],
        expected_decisions=["replace LRU with TTL"],
        expected_errors=["memory leak in cache layer"],
        test_query="What caused the memory leak and how was it fixed?",
        expected_answer_keywords=["LRU", "TTL", "garbage collection", "src/cache/lru.py", "verified"],
        protected_terms=["src/cache/ttl.py"],
    )


def v2_rich_pso_scenario() -> EvalScenario:
    """PSO with all v2 fields populated."""
    pid = "proj_v2_pso"
    sid = "sess_v2_003"
    events = [
        _evt(pid, sid, "user_message", "Development phase. Branch: feature/auth-v2. Milestone: v1.2-security."),
        _evt(pid, sid, "user_message", "Blocked: OAuth integration tests failing due to missing Google credentials."),
        _evt(pid, sid, "assistant_response", "Decision: use mock OAuth for tests, real OAuth only in staging."),
        _evt(pid, sid, "code_change", "Added mock OAuth provider.", {"file_path": "tests/auth/mock_oauth.py"}),
        _evt(pid, sid, "tool_call", "pytest auth tests: 8 passed, 2 failed (real OAuth missing)", {"tool_name": "pytest"}),
        _evt(pid, sid, "user_message", "Risk: shipping without real OAuth testing may break prod login."),
        _evt(pid, sid, "user_message", "Experiment: evaluating zero-trust architecture for internal APIs."),
    ]
    return EvalScenario(
        name="v2_rich_pso",
        project_id=pid,
        events=events,
        expected_goals=["complete auth refactor for v1.2"],
        expected_decisions=["use mock OAuth for tests"],
        expected_errors=["OAuth integration tests"],
        test_query="What is the current project state for auth refactor?",
        expected_answer_keywords=["development phase", "feature/auth-v2", "v1.2-security", "mock OAuth", "blocked", "risk", "experiment"],
        protected_terms=["feature/auth-v2", "v1.2-security", "mock_oauth.py"],
    )


def v2_contradiction_scenario() -> EvalScenario:
    """Active decision contradiction with v2 fields."""
    pid = "proj_v2_contra"
    sid = "sess_v2_004"
    events = [
        _evt(pid, sid, "user_message", (
            "Decision: use REST for all APIs. "
            "Rationale: team familiarity and existing tooling. "
            "Alternative: GraphQL — better for mobile clients but steeper learning curve."
        )),
        _evt(pid, sid, "code_change", "Added REST controllers.", {"file_path": "src/api/rest.py"}),
        _evt(pid, sid, "user_message", (
            "New requirement: mobile clients need flexible queries. "
            "Decision: migrate to GraphQL. REST is too rigid. "
            "Rationale: mobile performance critical. "
            "Tradeoff: team retraining needed, 2-week migration cost."
        )),
        _evt(pid, sid, "code_change", "Added GraphQL schema.", {"file_path": "src/api/graphql.py"}),
    ]
    return EvalScenario(
        name="v2_contradiction",
        project_id=pid,
        events=events,
        expected_goals=["support mobile clients"],
        expected_decisions=["migrate to GraphQL"],
        expected_errors=[],
        stale_facts=["use REST for all APIs"],
        test_query="What API technology should we use?",
        expected_answer_keywords=["GraphQL", "mobile", "REST"],
        protected_terms=["src/api/graphql.py"],
    )


def load_v2_enriched_scenarios():
    return [
        v2_rich_decision_scenario(),
        v2_rich_error_scenario(),
        v2_rich_pso_scenario(),
        v2_contradiction_scenario(),
    ]
