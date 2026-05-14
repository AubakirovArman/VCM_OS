from vcm_os.evals.scenarios.types import EvalScenario, _evt

def exact_config_key_scenario() -> EvalScenario:
    pid = 'proj_exact_cfg'
    sid = 'sess_cfg_001'
    events = [
        _evt(pid, sid, 'user_message', 'Requirement: disable FEATURE_AUTH_REFRESH_V2 in staging because it conflicts with the legacy SSO flow. Keep it enabled in production.'),
        _evt(pid, sid, 'assistant_response', "Decision: I'll update the environment config to set FEATURE_AUTH_REFRESH_V2=false for staging only."),
        _evt(pid, sid, 'code_change', 'Updated config/staging.yml: FEATURE_AUTH_REFRESH_V2=false', {"file_path": "config/staging.yml"}),
        _evt(pid, sid, 'tool_call', 'pytest config tests: 8 passed', {"tool_name": "pytest"}),
    ]
    return EvalScenario(
        name='exact_config_key',
        project_id=pid,
        events=events,
        expected_goals=['disable FEATURE_AUTH_REFRESH_V2 in staging'],
        expected_decisions=['set FEATURE_AUTH_REFRESH_V2=false for staging only'],
        expected_errors=[],
        test_query='Why is FEATURE_AUTH_REFRESH_V2 disabled?',
        expected_answer_keywords=[],
        protected_terms=['FEATURE_AUTH_REFRESH_V2'],
    )

def exact_api_endpoint_scenario() -> EvalScenario:
    pid = 'proj_exact_api'
    sid = 'sess_api_001'
    events = [
        _evt(pid, sid, 'user_message', 'The /api/v2/export/bulk endpoint needs rate limiting. Decision: apply 10 req/min per API key.'),
        _evt(pid, sid, 'code_change', 'Added rate limiter middleware for /api/v2/export/bulk', {"file_path": "src/api/v2/export.py"}),
        _evt(pid, sid, 'error', 'Load test shows /api/v2/export/bulk still allows burst traffic.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Fix: use token bucket instead of fixed window for /api/v2/export/bulk.'),
    ]
    return EvalScenario(
        name='exact_api_endpoint',
        project_id=pid,
        events=events,
        expected_goals=['The /api/v2/export/bulk endpoint needs rate limiting'],
        expected_decisions=['use token bucket instead of fixed window for /api/v2/export/bulk'],
        expected_errors=['Load test shows /api/v2/export/bulk still allows burst traffic'],
        test_query='What decision affects /api/v2/export/bulk?',
        expected_answer_keywords=[],
        protected_terms=['/api/v2/export/bulk'],
    )

def exact_cicd_job_scenario() -> EvalScenario:
    pid = 'proj_exact_cicd'
    sid = 'sess_cicd_001'
    events = [
        _evt(pid, sid, 'user_message', 'Error: The deploy-preview-h200 job is failing after the GitHub Actions migration. It cannot find the H200 runner label.'),
        _evt(pid, sid, 'assistant_response', "Decision: The runner label changed from h200-large to h200-standard. I'll update deploy-preview-h200 to use the new label."),
        _evt(pid, sid, 'code_change', 'Updated .github/workflows/preview.yml: deploy-preview-h200 uses runs-on: h200-standard', {"file_path": ".github/workflows/preview.yml"}),
        _evt(pid, sid, 'tool_call', 'CI check passed for deploy-preview-h200', {"tool_name": "github_actions"}),
    ]
    return EvalScenario(
        name='exact_cicd_job',
        project_id=pid,
        events=events,
        expected_goals=['The deploy-preview-h200 job is failing after the GitHub Actions migration'],
        expected_decisions=['The runner label changed from h200-large to h200-standard'],
        expected_errors=['It cannot find the H200 runner label'],
        test_query='Why did deploy-preview-h200 fail after migration?',
        expected_answer_keywords=[],
        protected_terms=['deploy-preview-h200', 'h200-large', 'h200-standard'],
    )

def exact_cve_scenario() -> EvalScenario:
    pid = 'proj_exact_cve'
    sid = 'sess_cve_001'
    events = [
        _evt(pid, sid, 'user_message', 'Security alert: CVE-2026-1234 affects our numpy dependency. We must upgrade to 1.26.4 immediately.'),
        _evt(pid, sid, 'assistant_response', 'Decision: pin numpy>=1.26.4 and run security audit for CVE-2026-1234.'),
        _evt(pid, sid, 'code_change', 'Updated requirements.txt: numpy>=1.26.4', {"file_path": "requirements.txt"}),
        _evt(pid, sid, 'tool_call', 'Security scan: no remaining traces of CVE-2026-1234', {"tool_name": "safety"}),
    ]
    return EvalScenario(
        name='exact_cve',
        project_id=pid,
        events=events,
        expected_goals=['CVE-2026-1234 affects our numpy dependency'],
        expected_decisions=['pin numpy>=1.26.4 and run security audit for CVE-2026-1234'],
        expected_errors=[],
        test_query='What patch decision was made for CVE-2026-1234?',
        expected_answer_keywords=[],
        protected_terms=['CVE-2026-1234', 'numpy>=1.26.4'],
    )

