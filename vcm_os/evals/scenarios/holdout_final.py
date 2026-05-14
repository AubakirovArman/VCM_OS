from vcm_os.evals.scenarios.types import EvalScenario, _evt

def security_remediation_scenario() -> EvalScenario:
    pid = "proj_holdout_18"
    sid = "sess_h18_001"
    events = [
        _evt(pid, sid, "user_message", "Security audit: SQL injection possible in search endpoint."),
        _evt(pid, sid, "user_message", "Decision: use parameterized queries everywhere. No raw SQL in search."),
        _evt(pid, sid, "code_change", "Replaced raw SQL with ORM queries in search.", {"file_path": "src/search/query.py"}),
        _evt(pid, sid, "tool_call", "Penetration test passed: no SQL injection vectors found.", {"tool_name": "burp"}),
    ]
    return EvalScenario(
        name="holdout_security_remediation",
        project_id=pid,
        events=events,
        expected_goals=["fix SQL injection"],
        expected_decisions=["use parameterized queries everywhere"],
        expected_errors=["SQL injection possible"],
        test_query="What was the SQL injection fix?",
        expected_answer_keywords=["parameterized queries", "ORM queries"],
        critical_gold=["parameterized queries"],
        protected_terms=["src/search/query.py", "SQL injection"],
        locked=True,
    )


def schema_evolution_scenario() -> EvalScenario:
    pid = "proj_holdout_19"
    sid = "sess_h19_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: add JSONB metadata column to users table."),
        _evt(pid, sid, "code_change", "Added migration: ALTER TABLE users ADD COLUMN metadata JSONB.", {"file_path": "migrations/2024_003_add_metadata.sql"}),
        _evt(pid, sid, "error", "Query performance degraded: JSONB metadata causing sequential scans.", {"error_kind": "performance"}),
        _evt(pid, sid, "user_message", "Decision: create GIN index on metadata and cache hot keys in Redis."),
        _evt(pid, sid, "code_change", "Created GIN index and Redis cache layer.", {"file_path": "migrations/2024_004_add_metadata_index.sql"}),
    ]
    return EvalScenario(
        name="holdout_schema_evolution",
        project_id=pid,
        events=events,
        expected_goals=["fast JSONB queries"],
        expected_decisions=["create GIN index on metadata"],
        expected_errors=["Query performance degraded"],
        test_query="How was the JSONB metadata performance fixed?",
        expected_answer_keywords=["GIN index", "Redis"],
        critical_gold=["GIN index"],
        protected_terms=["migrations/2024_003_add_metadata.sql", "migrations/2024_004_add_metadata_index.sql", "JSONB"],
        locked=True,
    )


def exact_package_name_scenario() -> EvalScenario:
    pid = "proj_holdout_20"
    sid = "sess_h20_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: replace lodash with radash for better tree-shaking."),
        _evt(pid, sid, "code_change", "Replaced lodash imports with radash.", {"file_path": "package.json"}),
        _evt(pid, sid, "error", "Build failed: radash does not have deepMerge function.", {"error_kind": "build_failure"}),
        _evt(pid, sid, "user_message", "Decision: use remeda instead of radash. It has deepMerge and tree-shaking."),
        _evt(pid, sid, "code_change", "Switched to remeda.", {"file_path": "package.json"}),
    ]
    return EvalScenario(
        name="holdout_exact_package_name",
        project_id=pid,
        events=events,
        expected_goals=["lodash replacement"],
        expected_decisions=["use remeda instead of radash"],
        expected_errors=["Build failed"],
        stale_facts=["replace lodash with radash"],
        test_query="What lodash replacement library are we using?",
        expected_answer_keywords=["remeda"],
        critical_gold=["remeda"],
        protected_terms=["remeda", "radash", "lodash", "package.json", "deepMerge"],
        locked=True,
    )


