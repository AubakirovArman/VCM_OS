# Backward-compatible shim — re-exports from modular sub-modules
from vcm_os.evals.scenarios.types import EvalScenario, _evt
from vcm_os.evals.scenarios.scenarios_core import (
    auth_refresh_loop_scenario,
    payment_rewrite_scenario,
    database_migration_scenario,
    api_versioning_scenario,
    microservices_decomposition_scenario,
    cache_invalidation_scenario,
    race_condition_scenario,
)
from vcm_os.evals.scenarios.scenarios_infra import (
    security_patch_scenario,
    feature_flag_scenario,
    cicd_migration_scenario,
    oauth_to_saml_scenario,
    rate_limiting_scenario,
    data_export_scenario,
    frontend_framework_scenario,
    logging_overhaul_scenario,
)
from vcm_os.evals.scenarios.scenarios_search import (
    search_optimization_scenario,
    search_optimization_regression_scenario,
    background_job_queue_scenario,
    multi_tenancy_scenario,
    config_management_scenario,
)
from vcm_os.evals.scenarios.scenarios_edge import (
    false_memory_s05,
    project_switching_h03,
    superseded_decision_scenario,
)
from vcm_os.evals.scenarios.scenarios_exact import (
    exact_config_key_scenario,
    exact_api_endpoint_scenario,
    exact_cicd_job_scenario,
    exact_cve_scenario,
)
from vcm_os.evals.scenarios.loader import load_all_scenarios, auth_refresh_loop_project

__all__ = [
    "EvalScenario",
    "_evt",
    "auth_refresh_loop_scenario",
    "payment_rewrite_scenario",
    "database_migration_scenario",
    "api_versioning_scenario",
    "microservices_decomposition_scenario",
    "cache_invalidation_scenario",
    "race_condition_scenario",
    "security_patch_scenario",
    "feature_flag_scenario",
    "cicd_migration_scenario",
    "oauth_to_saml_scenario",
    "rate_limiting_scenario",
    "data_export_scenario",
    "frontend_framework_scenario",
    "logging_overhaul_scenario",
    "config_management_scenario",
    "search_optimization_scenario",
    "search_optimization_regression_scenario",
    "background_job_queue_scenario",
    "multi_tenancy_scenario",
    "false_memory_s05",
    "project_switching_h03",
    "superseded_decision_scenario",
    "exact_config_key_scenario",
    "exact_api_endpoint_scenario",
    "exact_cicd_job_scenario",
    "exact_cve_scenario",
    "load_all_scenarios",
    "auth_refresh_loop_project",
]
