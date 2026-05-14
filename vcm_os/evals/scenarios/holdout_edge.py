from vcm_os.evals.scenarios.types import EvalScenario, _evt

def migration_rollback_scenario() -> EvalScenario:
    pid = "proj_holdout_13"
    sid = "sess_h13_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: deploy migration 2024_001_add_user_table."),
        _evt(pid, sid, "code_change", "Created migration 2024_001.", {"file_path": "migrations/2024_001_add_user_table.sql"}),
        _evt(pid, sid, "error", "Migration failed: duplicate column name in production.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: rollback migration 2024_001. Fix and redeploy as 2024_002."),
        _evt(pid, sid, "code_change", "Created migration 2024_002 with fix.", {"file_path": "migrations/2024_002_add_user_table_fixed.sql"}),
    ]
    return EvalScenario(
        name="holdout_migration_rollback",
        project_id=pid,
        events=events,
        expected_goals=["fixed migration"],
        expected_decisions=["rollback migration 2024_001"],
        expected_errors=["Migration failed"],
        stale_facts=["deploy migration 2024_001_add_user_table"],
        test_query="What migration should be deployed?",
        expected_answer_keywords=["2024_002", "rollback"],
        critical_gold=["2024_002"],
        protected_terms=["migrations/2024_001_add_user_table.sql", "migrations/2024_002_add_user_table_fixed.sql"],
        locked=True,
    )


def exact_api_version_scenario() -> EvalScenario:
    pid = "proj_holdout_14"
    sid = "sess_h14_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: API v3 uses /api/v3/graphql instead of REST."),
        _evt(pid, sid, "code_change", "Added GraphQL endpoint.", {"file_path": "src/api/graphql.py"}),
        _evt(pid, sid, "user_message", "Decision: keep REST for /api/v1 and /api/v2. v3 is GraphQL only."),
    ]
    return EvalScenario(
        name="holdout_exact_api_version",
        project_id=pid,
        events=events,
        expected_goals=["GraphQL v3"],
        expected_decisions=["API v3 uses /api/v3/graphql"],
        expected_errors=[],
        test_query="What API version uses GraphQL?",
        expected_answer_keywords=["/api/v3/graphql"],
        critical_gold=["/api/v3/graphql"],
        protected_terms=["/api/v3/graphql", "/api/v1", "/api/v2", "src/api/graphql.py"],
        locked=True,
    )


def test_flake_scenario() -> EvalScenario:
    pid = "proj_holdout_15"
    sid = "sess_h15_001"
    events = [
        _evt(pid, sid, "error", "Flaky test: test_checkout_flow fails 30% of runs.", {"error_kind": "test_failure"}),
        _evt(pid, sid, "user_message", "Decision: add retry logic with exponential backoff in test."),
        _evt(pid, sid, "code_change", "Added retry decorator to test_checkout_flow.", {"file_path": "tests/e2e/test_checkout.py"}),
        _evt(pid, sid, "error", "Flaky test still fails: root cause is race condition in payment webhook.", {"error_kind": "test_failure"}),
        _evt(pid, sid, "user_message", "Decision: mock payment webhook in e2e tests. Use contract tests for webhook."),
    ]
    return EvalScenario(
        name="holdout_test_flake",
        project_id=pid,
        events=events,
        expected_goals=["fix flaky test"],
        expected_decisions=["mock payment webhook in e2e tests"],
        expected_errors=["Flaky test", "race condition in payment webhook"],
        test_query="What was the fix for the flaky checkout test?",
        expected_answer_keywords=["mock payment webhook", "contract tests"],
        critical_gold=["mock payment webhook"],
        protected_terms=["tests/e2e/test_checkout.py", "payment webhook"],
        locked=True,
    )


def config_key_stress_scenario() -> EvalScenario:
    pid = "proj_holdout_16"
    sid = "sess_h16_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: enable FEATURE_DARK_MODE_V2 for all users."),
        _evt(pid, sid, "code_change", "Added FEATURE_DARK_MODE_V2 toggle.", {"file_path": "src/features/toggles.py"}),
        _evt(pid, sid, "user_message", "Decision: FEATURE_DARK_MODE_V1 is deprecated. Do not use."),
        _evt(pid, sid, "user_message", "Decision: FEATURE_BETA_AI_SUGGESTIONS requires opt-in consent."),
        _evt(pid, sid, "code_change", "Added consent gate for FEATURE_BETA_AI_SUGGESTIONS.", {"file_path": "src/features/consent.py"}),
        _evt(pid, sid, "user_message", "Decision: FEATURE_LEGACY_EXPORT must be disabled by 2026-06-01."),
    ]
    return EvalScenario(
        name="holdout_config_key_stress",
        project_id=pid,
        events=events,
        expected_goals=["feature toggles"],
        expected_decisions=["enable FEATURE_DARK_MODE_V2"],
        expected_errors=[],
        stale_facts=["FEATURE_DARK_MODE_V1"],
        test_query="What is the current dark mode feature flag?",
        expected_answer_keywords=["FEATURE_DARK_MODE_V2"],
        critical_gold=["FEATURE_DARK_MODE_V2"],
        protected_terms=["FEATURE_DARK_MODE_V2", "FEATURE_DARK_MODE_V1", "FEATURE_BETA_AI_SUGGESTIONS", "FEATURE_LEGACY_EXPORT"],
        locked=True,
    )


def dependency_conflict_scenario() -> EvalScenario:
    pid = "proj_holdout_17"
    sid = "sess_h17_001"
    events = [
        _evt(pid, sid, "error", "Dependency conflict: requests==2.31.0 requires urllib3<2, but boto3 requires urllib3>=2.", {"error_kind": "build_failure"}),
        _evt(pid, sid, "user_message", "Decision: pin urllib3==2.0.7 and upgrade requests to 2.32.0."),
        _evt(pid, sid, "code_change", "Updated requirements.txt.", {"file_path": "requirements.txt"}),
    ]
    return EvalScenario(
        name="holdout_dependency_conflict",
        project_id=pid,
        events=events,
        expected_goals=["resolve dependency conflict"],
        expected_decisions=["pin urllib3==2.0.7"],
        expected_errors=["Dependency conflict"],
        test_query="How was the urllib3 conflict resolved?",
        expected_answer_keywords=["urllib3==2.0.7", "requests to 2.32.0"],
        critical_gold=["urllib3==2.0.7"],
        protected_terms=["urllib3", "requests==2.31.0", "boto3", "requirements.txt"],
        locked=True,
    )


