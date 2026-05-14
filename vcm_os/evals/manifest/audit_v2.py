"""Extended audit with mutation log vs result validation."""
from typing import Dict, List

from vcm_os.evals.mutation_log import MutationLog
from vcm_os.evals.scenarios.types import EvalScenario


def validate_result_ids(
    holdout_scenarios: List[EvalScenario],
    mutation_log: MutationLog,
) -> Dict:
    """Validate that all frozen scenario IDs from mutation log ran in the result set."""
    run_names = [sc.name for sc in holdout_scenarios]
    return mutation_log.validate_against_run(run_names)


def validate_mutation_integrity(
    holdout_scenarios: List[EvalScenario],
    mutation_log: MutationLog,
) -> Dict:
    """Combined audit: inclusion + split purity + mutation log check."""
    from vcm_os.evals.manifest.audit import validate_frozen_inclusion, validate_split_purity
    from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios

    tuning = load_all_scenarios()
    holdout = holdout_scenarios

    inclusion = validate_frozen_inclusion(holdout, [])
    purity = validate_split_purity(tuning, holdout)
    result_check = validate_result_ids(holdout, mutation_log)

    all_ok = (
        inclusion["all_frozen_scenarios_ran"]
        and purity["split_purity_ok"]
        and result_check["all_frozen_present"]
    )

    return {
        "audit_passed": all_ok,
        "inclusion": inclusion,
        "split_purity": purity,
        "mutation_log_check": result_check,
    }
