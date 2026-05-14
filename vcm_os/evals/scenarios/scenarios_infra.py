from vcm_os.evals.scenarios.types import EvalScenario, _evt

def security_patch_scenario() -> EvalScenario:
    pid = 'proj_sec'
    sid = 'sess_sec_001'
    events = [
        _evt(pid, sid, 'user_message', 'CVE-2026-1234: SQL injection in search endpoint. Must patch today.'),
        _evt(pid, sid, 'assistant_response', 'Found unsanitized query parameter in search.py.'),
        _evt(pid, sid, 'code_change', 'Added parameterized queries to search.', {"file_path": "src/search/query.py"}),
        _evt(pid, sid, 'error', 'Regression: search stopped supporting wildcard patterns.', {"error_kind": "test_failure"}),
        _evt(pid, sid, 'user_message', 'Decision: use prepared statements but preserve wildcard support via LIKE.'),
        _evt(pid, sid, 'code_change', 'Updated to use LIKE with parameterized patterns.', {"file_path": "src/search/query.py"}),
        _evt(pid, sid, 'user_message', 'Decision: all DB queries must use parameterized statements. No exceptions.'),
    ]
    return EvalScenario(
        name='security_patch',
        project_id=pid,
        events=events,
        expected_goals=['patch SQL injection'],
        expected_decisions=['use prepared statements', 'all DB queries must use parameterized statements'],
        expected_errors=['regression'],
        test_query='LIKE',
        expected_answer_keywords=['wildcard patterns'],
        critical_gold=['What is the query security policy?', 'parameterized'],
    )

def feature_flag_scenario() -> EvalScenario:
    pid = 'proj_flags'
    sid = 'sess_flags_001'
    events = [
        _evt(pid, sid, 'user_message', 'Implement feature flags for new dashboard. Must be toggleable without deploy.'),
        _evt(pid, sid, 'assistant_response', 'Using LaunchDarkly-like config in Redis.'),
        _evt(pid, sid, 'code_change', 'Added feature flag evaluator.', {"file_path": "src/flags/evaluator.py"}),
        _evt(pid, sid, 'error', 'Flags not syncing: Redis cache shows old values for 30s.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use Pub/Sub for flag updates with 100ms propagation SLA.'),
        _evt(pid, sid, 'code_change', 'Implemented Redis Pub/Sub for flag sync.', {"file_path": "src/flags/sync.py"}),
    ]
    return EvalScenario(
        name='feature_flags',
        project_id=pid,
        events=events,
        expected_goals=['feature flags'],
        expected_decisions=['use Pub/Sub for flag updates'],
        expected_errors=['not syncing'],
        test_query='100ms SLA',
        expected_answer_keywords=['How do feature flags propagate?', 'Pub/Sub'],
    )

def cicd_migration_scenario() -> EvalScenario:
    pid = 'proj_cicd'
    sid = 'sess_cicd_001'
    events = [
        _evt(pid, sid, 'user_message', 'Migrate from Jenkins to GitHub Actions. Must keep build times under 10 minutes.'),
        _evt(pid, sid, 'assistant_response', 'Will parallelize test suites and cache dependencies.'),
        _evt(pid, sid, 'code_change', 'Created GitHub Actions workflow.', {"file_path": ".github/workflows/ci.yml"}),
        _evt(pid, sid, 'error', 'Build time 18 minutes: integration tests not parallelized.', {"error_kind": "test_failure"}),
        _evt(pid, sid, 'user_message', 'Decision: split integration tests into 4 shards. Run unit tests in parallel.'),
        _evt(pid, sid, 'code_change', 'Added test sharding.', {"file_path": ".github/workflows/ci.yml"}),
        _evt(pid, sid, 'tool_call', 'Build time: 7 minutes.', {"tool_name": "github_actions"}),
    ]
    return EvalScenario(
        name='cicd_migration',
        project_id=pid,
        events=events,
        expected_goals=['Jenkins to GitHub Actions'],
        expected_decisions=['split integration tests into 4 shards'],
        expected_errors=['build time 18 minutes'],
        test_query='What is the CI build time target?',
        expected_answer_keywords=[],
    )

def oauth_to_saml_scenario() -> EvalScenario:
    pid = 'proj_auth2'
    sid = 'sess_auth2_001'
    events = [
        _evt(pid, sid, 'user_message', 'Migrate auth from OAuth2 to SAML for enterprise customers.'),
        _evt(pid, sid, 'assistant_response', 'Will support both via strategy pattern.'),
        _evt(pid, sid, 'code_change', 'Added SAML strategy.', {"file_path": "src/auth/saml.py"}),
        _evt(pid, sid, 'error', 'SAML assertion validation failing: clock skew > 5 minutes.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: allow clock skew up to 10 minutes. Log warnings if > 5 minutes.'),
        _evt(pid, sid, 'code_change', 'Updated clock skew tolerance.', {"file_path": "src/auth/saml.py"}),
        _evt(pid, sid, 'user_message', 'Decision: OAuth2 stays for non-enterprise. SAML only for enterprise tier.'),
    ]
    return EvalScenario(
        name='oauth_to_saml',
        project_id=pid,
        events=events,
        expected_goals=['OAuth2 to SAML'],
        expected_decisions=['allow clock skew up to 10 minutes', 'OAuth2 stays for non-enterprise'],
        expected_errors=['assertion validation failing'],
        test_query='What auth methods do we support?',
        expected_answer_keywords=[],
    )

def rate_limiting_scenario() -> EvalScenario:
    pid = 'proj_rate'
    sid = 'sess_rate_001'
    events = [
        _evt(pid, sid, 'user_message', 'Add rate limiting to public API. 100 req/min per key, 1000 req/min per IP.'),
        _evt(pid, sid, 'assistant_response', 'Using token bucket in Redis.'),
        _evt(pid, sid, 'code_change', 'Added Redis token bucket.', {"file_path": "src/rate/limiter.py"}),
        _evt(pid, sid, 'error', 'Rate limiter allowing bursts > 1000: window reset race condition.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use sliding window, not fixed window.'),
        _evt(pid, sid, 'code_change', 'Replaced fixed window with sliding window.', {"file_path": "src/rate/limiter.py"}),
    ]
    return EvalScenario(
        name='rate_limiting',
        project_id=pid,
        events=events,
        expected_goals=['sliding window'],
        expected_decisions=['use sliding window, not fixed window'],
        expected_errors=['bursts'],
        test_query='not fixed window',
        expected_answer_keywords=['What rate limiting algorithm do we use?', 'sliding window'],
    )

def data_export_scenario() -> EvalScenario:
    pid = 'proj_export'
    sid = 'sess_export_001'
    events = [
        _evt(pid, sid, 'user_message', 'Implement GDPR data export. Must include all user data in machine-readable format.'),
        _evt(pid, sid, 'assistant_response', 'Will generate JSON export with all related entities.'),
        _evt(pid, sid, 'code_change', 'Added data export generator.', {"file_path": "src/export/generator.py"}),
        _evt(pid, sid, 'error', 'Export timing out for users with >10k orders: O(n^2) query.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use cursor-based pagination and background job for large exports.'),
        _evt(pid, sid, 'code_change', 'Implemented cursor pagination and queue.', {"file_path": "src/export/queue.py"}),
    ]
    return EvalScenario(
        name='data_export',
        project_id=pid,
        events=events,
        expected_goals=['GDPR export'],
        expected_decisions=['use cursor-based pagination'],
        expected_errors=['timing out'],
        test_query='background job',
        expected_answer_keywords=['How are large exports handled?', 'cursor-based pagination'],
    )

def frontend_framework_scenario() -> EvalScenario:
    pid = 'proj_fe'
    sid = 'sess_fe_001'
    events = [
        _evt(pid, sid, 'user_message', 'Migrate from Angular to React. Must keep existing routing structure.'),
        _evt(pid, sid, 'assistant_response', 'Will use React Router to match Angular routes.'),
        _evt(pid, sid, 'code_change', 'Created React components for main pages.', {"file_path": "frontend/src/App.tsx"}),
        _evt(pid, sid, 'error', 'Route guards not working: unauthorized users accessing admin routes.', {"error_kind": "test_failure"}),
        _evt(pid, sid, 'user_message', 'Decision: implement auth guards in React Router loaders.'),
        _evt(pid, sid, 'code_change', 'Added auth guard loaders.', {"file_path": "frontend/src/router/guards.ts"}),
    ]
    return EvalScenario(
        name='frontend_migration',
        project_id=pid,
        events=events,
        expected_goals=['Angular to React'],
        expected_decisions=['implement auth guards in React Router loaders'],
        expected_errors=['route guards not working'],
        test_query='React Router loaders',
        expected_answer_keywords=['How is auth handled in React Router?', 'auth guards'],
    )

def logging_overhaul_scenario() -> EvalScenario:
    pid = 'proj_logs'
    sid = 'sess_logs_001'
    events = [
        _evt(pid, sid, 'user_message', 'Logs are unstructured and missing trace IDs. Use structured JSON logging.'),
        _evt(pid, sid, 'assistant_response', 'Will add correlation-id middleware and JSON formatter.'),
        _evt(pid, sid, 'code_change', 'Added correlation-id middleware.', {"file_path": "src/middleware/correlation.py"}),
        _evt(pid, sid, 'error', 'Log volume increased 10x: PII leaking into logs.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: redact email, phone, SSN from all log fields automatically.'),
        _evt(pid, sid, 'code_change', 'Added PII redaction filter.', {"file_path": "src/logging/redact.py"}),
    ]
    return EvalScenario(
        name='logging_overhaul',
        project_id=pid,
        events=events,
        expected_goals=['structured JSON logging'],
        expected_decisions=['redact email, phone, SSN'],
        expected_errors=['PII leaking'],
        test_query='redact',
        expected_answer_keywords=['What PII fields are redacted in logs?', 'PII'],
    )

