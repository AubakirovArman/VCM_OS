"""Hard adversarial scenarios with 20+ distracting memories.

These scenarios test whether sparse retrieval can differentiate exact symbols
when vector retrieval is swamped by semantically similar distractors.
"""

from typing import List
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario, _evt


def _many_distractors(
    project_id: str,
    session_id: str,
    base_name: str,
    correct_value: str,
    distractors: List[str],
    query: str,
    expected_keywords: List[str],
    critical_gold: List[str],
    protected_terms: List[str],
) -> EvalScenario:
    events = []
    for d in distractors:
        events.append(_evt(project_id, session_id, "user_message", f"Decision: {base_name} must be {d}."))
        events.append(_evt(project_id, session_id, "code_change", f"Configured {base_name} = {d}.", {"file_path": f"config/{d.replace('/', '_')}.yaml"}))
    # Correct one LAST — tests recency too
    events.append(_evt(project_id, session_id, "user_message", f"Decision: {base_name} is now {correct_value}. Override all previous configs."))
    events.append(_evt(project_id, session_id, "code_change", f"Final config: {base_name} = {correct_value}.", {"file_path": "config/final.yaml"}))
    return EvalScenario(
        name=f"adversarial_hard_{base_name.replace(' ', '_').lower()}",
        project_id=project_id,
        events=events,
        expected_goals=[f"set {base_name} to {correct_value}"],
        expected_decisions=[f"{base_name} is now {correct_value}"],
        expected_errors=[],
        test_query=query,
        expected_answer_keywords=expected_keywords,
        critical_gold=critical_gold,
        protected_terms=protected_terms,
        locked=True,
    )


def adversarial_hard_api_endpoints() -> EvalScenario:
    distractors = [f"/api/v1/{r}" for r in [
        "users", "orders", "products", "inventory", "shipping",
        "billing", "analytics", "reports", "webhooks", "health",
        "metrics", "logs", "alerts", "settings", "permissions",
        "roles", "sessions", "tokens", "uploads", "exports"
    ]]
    return _many_distractors(
        project_id="proj_adv_hard_01",
        session_id="sess_ah01_001",
        base_name="export endpoint",
        correct_value="/api/v1/exports/bulk",
        distractors=distractors,
        query="What is the bulk export API endpoint?",
        expected_keywords=["/api/v1/exports/bulk"],
        critical_gold=["/api/v1/exports/bulk"],
        protected_terms=["/api/v1/exports/bulk", "config/final.yaml"],
    )


def adversarial_hard_env_vars() -> EvalScenario:
    distractors = [f"DB_HOST_{i}" for i in range(20)]
    return _many_distractors(
        project_id="proj_adv_hard_02",
        session_id="sess_ah02_001",
        base_name="primary database host",
        correct_value="DB_HOST_PROD_RW",
        distractors=distractors,
        query="What is the primary production database host env var?",
        expected_keywords=["DB_HOST_PROD_RW"],
        critical_gold=["DB_HOST_PROD_RW"],
        protected_terms=["DB_HOST_PROD_RW", "config/final.yaml"],
    )


def adversarial_hard_feature_flags() -> EvalScenario:
    distractors = [f"FEATURE_ENABLE_{f}" for f in [
        "dark_mode", "beta_ui", "new_nav", "ai_chat", "voice_search",
        "payments_v2", "subscriptions", "analytics", "notifications",
        "offline_mode", "sync", "backup", "encryption", "sso",
        "mfa", "audit_log", "rate_limit", "webhooks", "graphql",
        "rest_v3"
    ]]
    return _many_distractors(
        project_id="proj_adv_hard_03",
        session_id="sess_ah03_001",
        base_name="checkout flow feature flag",
        correct_value="FEATURE_ENABLE_CHECKOUT_V2",
        distractors=distractors,
        query="What feature flag controls the checkout flow?",
        expected_keywords=["FEATURE_ENABLE_CHECKOUT_V2"],
        critical_gold=["FEATURE_ENABLE_CHECKOUT_V2"],
        protected_terms=["FEATURE_ENABLE_CHECKOUT_V2", "config/final.yaml"],
    )


def adversarial_hard_migration_numbers() -> EvalScenario:
    distractors = [f"2024_{i:03d}_migration" for i in range(20)]
    return _many_distractors(
        project_id="proj_adv_hard_04",
        session_id="sess_ah04_001",
        base_name="latest migration",
        correct_value="2024_021_add_user_consent",
        distractors=distractors,
        query="What is the latest migration file?",
        expected_keywords=["2024_021_add_user_consent"],
        critical_gold=["2024_021_add_user_consent"],
        protected_terms=["2024_021_add_user_consent", "config/final.yaml"],
    )


def adversarial_hard_package_versions() -> EvalScenario:
    distractors = [f"1.{i}.0" for i in range(20)]
    return _many_distractors(
        project_id="proj_adv_hard_05",
        session_id="sess_ah05_001",
        base_name="API client version",
        correct_value="1.15.0",
        distractors=distractors,
        query="What version of the API client are we using?",
        expected_keywords=["1.15.0"],
        critical_gold=["1.15.0"],
        protected_terms=["1.15.0", "config/final.yaml"],
    )


def load_adversarial_hard_scenarios() -> List[EvalScenario]:
    return [
        adversarial_hard_api_endpoints(),
        adversarial_hard_env_vars(),
        adversarial_hard_feature_flags(),
        adversarial_hard_migration_numbers(),
        adversarial_hard_package_versions(),
    ]
