# VCM-OS Holdout Mutation Log

## Rule

Any change to a locked scenario after its freeze date must be logged here with justification.
Allowed changes: evaluator bugfix only.
Forbidden changes: scenario text changes, expected keyword changes, decision text changes.

## Frozen Scenarios

| # | Scenario | Freeze Date | First Run Result | Status |
|---|----------|-------------|------------------|--------|
| 1 | auth_refresh_loop | 2026-05-10 | quality=1.667 restore=0.667 | locked |
| 2 | payment_rewrite | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 3 | db_migration | 2026-05-10 | quality=1.333 restore=0.667 | locked |
| 4 | api_versioning | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 5 | microservices_decomposition | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 6 | cache_invalidation | 2026-05-10 | quality=1.667 restore=1.000 | locked |
| 7 | race_condition | 2026-05-10 | quality=1.667 restore=1.000 | locked |
| 8 | security_patch | 2026-05-10 | quality=0.667 restore=1.000 | locked |
| 9 | feature_flags | 2026-05-10 | quality=1.500 restore=1.000 | locked |
| 10 | cicd_migration | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 11 | holdout_stale_migration | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 12 | holdout_exact_env_var | 2026-05-10 | quality=1.733 restore=0.667 | locked |
| 13 | holdout_superseded_cache | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 14 | holdout_exact_function_name | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 15 | holdout_multi_session_auth | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 16 | holdout_exact_cve_patch | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 17 | holdout_code_change_only | 2026-05-10 | quality=1.733 restore=0.667 | locked |
| 18 | holdout_error_only_debugging | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 19 | holdout_long_text_budget_stress | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 20 | holdout_contradiction_same_file | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 21 | holdout_exact_version | 2026-05-10 | quality=2.000 restore=1.000 | locked |
| 22 | holdout_multi_tenant_config | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 23 | holdout_migration_rollback | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 24 | holdout_exact_api_version | 2026-05-10 | quality=1.733 restore=0.667 | locked |
| 25 | holdout_test_flake | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 26 | holdout_config_key_stress | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 27 | holdout_dependency_conflict | 2026-05-10 | quality=1.733 restore=0.667 | locked |
| 28 | holdout_security_remediation | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 29 | holdout_schema_evolution | 2026-05-10 | quality=1.400 restore=0.667 | locked |
| 30 | holdout_exact_package_name | 2026-05-10 | quality=1.733 restore=0.667 | locked |

## Changelog

```
2026-05-10: Initial freeze of 10 holdout scenarios.
           No mutations since freeze.
2026-05-10: Expanded holdout to 30 scenarios (added 20 new).
           No mutations since freeze.
```
