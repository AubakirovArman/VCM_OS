from typing import List
from vcm_os.evals.scenarios.types import EvalScenario
from vcm_os.evals.scenarios.holdout_core import (
    stale_migration_scenario,
    exact_env_var_scenario,
    superseded_cache_scenario,
    exact_function_name_scenario,
    multi_session_auth_scenario,
)
from vcm_os.evals.scenarios.holdout_exact import (
    exact_cve_patch_scenario,
    code_change_only_decision_scenario,
    error_only_debugging_scenario,
)
from vcm_os.evals.scenarios.holdout_stress import (
    long_text_budget_stress_scenario,
    contradiction_same_file_scenario,
    exact_version_scenario,
    multi_tenant_config_scenario,
)
from vcm_os.evals.scenarios.holdout_edge import (
    migration_rollback_scenario,
    exact_api_version_scenario,
    test_flake_scenario,
    config_key_stress_scenario,
    dependency_conflict_scenario,
)
from vcm_os.evals.scenarios.holdout_final import (
    security_remediation_scenario,
    schema_evolution_scenario,
    exact_package_name_scenario,
)

def load_holdout_scenarios():
    return [
        stale_migration_scenario(),
        exact_env_var_scenario(),
        superseded_cache_scenario(),
        exact_function_name_scenario(),
        multi_session_auth_scenario(),
        exact_cve_patch_scenario(),
        code_change_only_decision_scenario(),
        error_only_debugging_scenario(),
        long_text_budget_stress_scenario(),
        contradiction_same_file_scenario(),
        exact_version_scenario(),
        multi_tenant_config_scenario(),
        migration_rollback_scenario(),
        exact_api_version_scenario(),
        test_flake_scenario(),
        config_key_stress_scenario(),
        dependency_conflict_scenario(),
        security_remediation_scenario(),
        schema_evolution_scenario(),
        exact_package_name_scenario(),
    ]
