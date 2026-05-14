"""Dedicated project-state restore scenarios for I01 v2."""
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


def project_state_auth_scenario() -> EvalScenario:
    pid = "proj_pso_auth"
    sid = "sess_pso_001"
    events = [
        _evt(pid, sid, "user_message", "We are in testing phase for the auth refactor. Branch: feature/auth-v2. Milestone: v1.2-security."),
        _evt(pid, sid, "user_message", "Blocked: OAuth integration tests are failing because the test env lacks Google credentials."),
        _evt(pid, sid, "assistant_response", "Decision: use mock OAuth for tests, real OAuth only in staging."),
        _evt(pid, sid, "code_change", "Added mock OAuth provider for test suite.", {"file_path": "tests/auth/mock_oauth.py"}),
        _evt(pid, sid, "tool_call", "pytest auth tests: 8 passed, 2 failed (real OAuth missing)", {"tool_name": "pytest"}),
        _evt(pid, sid, "user_message", "Risk: if we ship without real OAuth testing, prod login may break."),
    ]
    return EvalScenario(
        name="pso_auth_refactor",
        project_id=pid,
        events=events,
        expected_goals=["complete auth refactor for v1.2"],
        expected_decisions=["use mock OAuth for tests"],
        expected_errors=["OAuth integration tests"],
        test_query="What is the current project state for auth refactor?",
        expected_answer_keywords=["testing phase", "feature/auth-v2", "v1.2-security", "mock OAuth", "blocked", "risk"],
        protected_terms=["feature/auth-v2", "v1.2-security", "mock_oauth.py"],
    )


def project_state_deployment_scenario() -> EvalScenario:
    pid = "proj_pso_deploy"
    sid = "sess_pso_002"
    events = [
        _evt(pid, sid, "user_message", "Deployment phase. Branch: release/v2.0. Milestone: production launch."),
        _evt(pid, sid, "user_message", "Staging deployment succeeded. All integration tests green."),
        _evt(pid, sid, "tool_call", "deploy to staging: success. Health checks passing.", {"tool_name": "deploy"}),
        _evt(pid, sid, "user_message", "Blocked: production rollout waiting for security audit sign-off."),
        _evt(pid, sid, "assistant_response", "Decision: do not deploy to prod until security audit completes."),
        _evt(pid, sid, "user_message", "Risk: delayed launch may miss marketing window."),
    ]
    return EvalScenario(
        name="pso_deployment",
        project_id=pid,
        events=events,
        expected_goals=["launch v2.0 to production"],
        expected_decisions=["do not deploy to prod"],
        expected_errors=[],
        test_query="What is the deployment status?",
        expected_answer_keywords=["deployment phase", "release/v2.0", "staging", "blocked", "security audit"],
        protected_terms=["release/v2.0", "production"],
    )


def project_state_bugfix_scenario() -> EvalScenario:
    pid = "proj_pso_bugfix"
    sid = "sess_pso_003"
    events = [
        _evt(pid, sid, "user_message", "Maintenance phase. Branch: hotfix/memory-leak. Milestone: v1.1.1-patch."),
        _evt(pid, sid, "user_message", "Memory leak in cache layer. Production alerts firing."),
        _evt(pid, sid, "assistant_response", "Decision: disable LRU cache, fallback to simple TTL."),
        _evt(pid, sid, "code_change", "Replaced LRU cache with TTL-based cache.", {"file_path": "src/cache/ttl_cache.py"}),
        _evt(pid, sid, "tool_call", "pytest cache tests: 15 passed, 0 failed", {"tool_name": "pytest"}),
        _evt(pid, sid, "user_message", "Blocked: cannot merge hotfix until QA validates on staging."),
    ]
    return EvalScenario(
        name="pso_bugfix",
        project_id=pid,
        events=events,
        expected_goals=["fix memory leak in production"],
        expected_decisions=["disable LRU cache"],
        expected_errors=["memory leak in cache layer"],
        test_query="What is the status of the memory leak fix?",
        expected_answer_keywords=["maintenance phase", "hotfix/memory-leak", "TTL cache", "blocked", "QA"],
        protected_terms=["hotfix/memory-leak", "ttl_cache.py"],
    )


def project_state_experiment_scenario() -> EvalScenario:
    pid = "proj_pso_experiment"
    sid = "sess_pso_004"
    events = [
        _evt(pid, sid, "user_message", "Development phase. Branch: experiment/graphql-migration. Milestone: v2.1-api."),
        _evt(pid, sid, "user_message", "Experiment: migrating REST to GraphQL. Spike in progress."),
        _evt(pid, sid, "assistant_response", "Decision: GraphQL schema auto-generated from OpenAPI spec."),
        _evt(pid, sid, "code_change", "Added GraphQL schema generator.", {"file_path": "src/api/graphql_gen.py"}),
        _evt(pid, sid, "tool_call", "pytest api tests: 5 passed, 3 failed (REST compatibility)", {"tool_name": "pytest"}),
        _evt(pid, sid, "user_message", "Risk: REST compatibility break may affect mobile clients."),
    ]
    return EvalScenario(
        name="pso_experiment",
        project_id=pid,
        events=events,
        expected_goals=["evaluate GraphQL migration"],
        expected_decisions=["GraphQL schema auto-generated"],
        expected_errors=["REST compatibility"],
        test_query="What experiments are active?",
        expected_answer_keywords=["development phase", "experiment/graphql-migration", "GraphQL", "risk"],
        protected_terms=["experiment/graphql-migration", "graphql_gen.py"],
    )


def project_state_multitask_scenario() -> EvalScenario:
    pid = "proj_pso_multi"
    sid = "sess_pso_005"
    events = [
        _evt(pid, sid, "user_message", "Planning phase. Branch: main. Milestone: v3.0-platform."),
        _evt(pid, sid, "user_message", "Open tasks: refactor auth, migrate DB, update docs."),
        _evt(pid, sid, "user_message", "Blocked: DB migration waiting for DBA approval."),
        _evt(pid, sid, "user_message", "Blocked: auth refactor waiting for security review."),
        _evt(pid, sid, "assistant_response", "Decision: docs update can proceed independently."),
        _evt(pid, sid, "code_change", "Updated API documentation.", {"file_path": "docs/api.md"}),
    ]
    return EvalScenario(
        name="pso_multitask",
        project_id=pid,
        events=events,
        expected_goals=["prepare v3.0 platform release"],
        expected_decisions=["docs update can proceed independently"],
        expected_errors=[],
        test_query="What tasks are blocked?",
        expected_answer_keywords=["planning phase", "main", "v3.0-platform", "blocked", "DB migration", "auth refactor"],
        protected_terms=["v3.0-platform", "api.md"],
    )


def load_project_state_scenarios():
    return [
        project_state_auth_scenario(),
        project_state_deployment_scenario(),
        project_state_bugfix_scenario(),
        project_state_experiment_scenario(),
        project_state_multitask_scenario(),
    ]
