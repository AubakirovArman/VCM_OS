"""Adversarial exact-symbol scenarios for v0.6.

These scenarios test whether VCM can distinguish near-duplicate technical
symbols that vector embeddings confuse but exact/sparse retrieval should
handle correctly.
"""

from typing import List

from vcm_os.evals.scenarios.synthetic_projects import EvalScenario, _evt


def adversarial_feature_flags_scenario() -> EvalScenario:
    """Vector may confuse sibling feature flags; exact retrieval must distinguish."""
    pid = "proj_adv_flags"
    sid = "sess_adv_flags_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: enable FEATURE_AUTH_REFRESH_V2 for all users."),
        _evt(pid, sid, "code_change", "Added FEATURE_AUTH_REFRESH_V2 gate.", {"file_path": "src/auth/refresh.py"}),
        _evt(pid, sid, "user_message", "Decision: disable FEATURE_AUTH_REFRESH_V3, it is not ready."),
        _evt(pid, sid, "code_change", "Removed FEATURE_AUTH_REFRESH_V3 stub.", {"file_path": "src/auth/refresh_v3.py"}),
        _evt(pid, sid, "user_message", "Decision: keep FEATURE_AUTH_REFRESH_LEGACY for enterprise customers only."),
        _evt(pid, sid, "code_change", "Scoped FEATURE_AUTH_REFRESH_LEGACY to enterprise tier.", {"file_path": "src/auth/legacy.py"}),
        _evt(pid, sid, "user_message", "Decision: FEATURE_AUTH_REFRESH_STAGING is deprecated. Do not use."),
        _evt(pid, sid, "code_change", "Removed FEATURE_AUTH_REFRESH_STAGING references.", {"file_path": "src/auth/staging.py"}),
        _evt(pid, sid, "user_message", "Decision: FEATURE_AUTH_REFRESH_PROD requires MFA."),
        _evt(pid, sid, "code_change", "Added MFA check for FEATURE_AUTH_REFRESH_PROD.", {"file_path": "src/auth/prod.py"}),
    ]
    return EvalScenario(
        name="adversarial_feature_flags",
        project_id=pid,
        events=events,
        expected_goals=["auth refresh feature flags"],
        expected_decisions=["enable FEATURE_AUTH_REFRESH_V2"],
        expected_errors=[],
        stale_facts=["FEATURE_AUTH_REFRESH_V3", "FEATURE_AUTH_REFRESH_STAGING"],
        test_query="What is the current auth refresh flag for all users?",
        expected_answer_keywords=["FEATURE_AUTH_REFRESH_V2", "enable"],
        critical_gold=["FEATURE_AUTH_REFRESH_V2"],
        protected_terms=["FEATURE_AUTH_REFRESH_V2", "FEATURE_AUTH_REFRESH_V3",
                         "FEATURE_AUTH_REFRESH_LEGACY", "FEATURE_AUTH_REFRESH_STAGING",
                         "FEATURE_AUTH_REFRESH_PROD"],
        locked=True,
    )


def adversarial_api_routes_scenario() -> EvalScenario:
    """Vector may confuse sibling API routes; exact retrieval must distinguish."""
    pid = "proj_adv_api"
    sid = "sess_adv_api_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: /api/v2/users/bulk is the new bulk user endpoint."),
        _evt(pid, sid, "code_change", "Implemented /api/v2/users/bulk.", {"file_path": "src/api/users_bulk.py"}),
        _evt(pid, sid, "user_message", "Decision: /api/v2/users/export is for GDPR exports only."),
        _evt(pid, sid, "code_change", "Added /api/v2/users/export with rate limiting.", {"file_path": "src/api/users_export.py"}),
        _evt(pid, sid, "user_message", "Decision: /api/v2/users/validate is internal only."),
        _evt(pid, sid, "code_change", "Created /api/v2/users/validate for internal health checks.", {"file_path": "src/api/users_validate.py"}),
        _evt(pid, sid, "user_message", "Decision: /api/v1/users/bulk is deprecated. Use v2."),
    ]
    return EvalScenario(
        name="adversarial_api_routes",
        project_id=pid,
        events=events,
        expected_goals=["bulk user endpoint"],
        expected_decisions=["/api/v2/users/bulk"],
        expected_errors=[],
        stale_facts=["/api/v1/users/bulk"],
        test_query="What is the current bulk user API endpoint?",
        expected_answer_keywords=["/api/v2/users/bulk"],
        critical_gold=["/api/v2/users/bulk"],
        protected_terms=["/api/v2/users/bulk", "/api/v2/users/export",
                         "/api/v2/users/validate", "/api/v1/users/bulk"],
        locked=True,
    )


def adversarial_job_names_scenario() -> EvalScenario:
    """CI job names with similar prefixes; exact retrieval must distinguish."""
    pid = "proj_adv_jobs"
    sid = "sess_adv_jobs_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: deploy-preview-h200 is the GPU preview job."),
        _evt(pid, sid, "code_change", "Created deploy-preview-h200 workflow.", {"file_path": ".github/workflows/deploy-preview-h200.yml"}),
        _evt(pid, sid, "user_message", "Decision: deploy-preview-standard is the CPU preview job."),
        _evt(pid, sid, "code_change", "Created deploy-preview-standard workflow.", {"file_path": ".github/workflows/deploy-preview-standard.yml"}),
        _evt(pid, sid, "user_message", "Decision: deploy-staging-h200 is for staging GPU tests."),
        _evt(pid, sid, "code_change", "Created deploy-staging-h200 workflow.", {"file_path": ".github/workflows/deploy-staging-h200.yml"}),
        _evt(pid, sid, "user_message", "Decision: deploy-prod-h200 is production GPU deployment."),
        _evt(pid, sid, "code_change", "Created deploy-prod-h200 workflow.", {"file_path": ".github/workflows/deploy-prod-h200.yml"}),
    ]
    return EvalScenario(
        name="adversarial_job_names",
        project_id=pid,
        events=events,
        expected_goals=["GPU preview deployment"],
        expected_decisions=["deploy-preview-h200"],
        expected_errors=[],
        test_query="What is the GPU preview CI job name?",
        expected_answer_keywords=["deploy-preview-h200"],
        critical_gold=["deploy-preview-h200"],
        protected_terms=["deploy-preview-h200", "deploy-preview-standard",
                         "deploy-staging-h200", "deploy-prod-h200"],
        locked=True,
    )


def load_adversarial_scenarios() -> List[EvalScenario]:
    return [
        adversarial_feature_flags_scenario(),
        adversarial_api_routes_scenario(),
        adversarial_job_names_scenario(),
    ]
