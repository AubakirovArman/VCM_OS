"""Build canonical evaluation manifest before a run."""
import vcm_os.evals.metrics as metrics_module
from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.manifest import (
    EvalManifest,
    hash_evaluator,
    hash_metrics_module,
    hash_module_file,
    hash_retrieval_config,
    hash_scenario_set,
)
from vcm_os.evals.manifest.audit_v2 import validate_mutation_integrity
from vcm_os.evals.mutation_log import MutationLog
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios


def build_manifest(
    system_version: str = "v0.5-gold",
    eval_phase: str = "v0.6-generalization",
    report_version: str = "",
) -> EvalManifest:
    """Construct a manifest from current code and scenarios."""
    tuning = load_all_scenarios()
    holdout = load_holdout_scenarios()

    manifest = EvalManifest(
        system_version=system_version,
        eval_phase=eval_phase,
        report_version=report_version,
    )

    # Code hashes
    manifest.evaluator_hash = hash_evaluator(
        ExperimentRunner,
        ExperimentRunner.score_pack,
    )
    manifest.metrics_hash = hash_metrics_module(metrics_module)
    manifest.pack_builder_hash = hash_module_file(
        __import__("vcm_os.context.pack_builder", fromlist=["pack_builder"])
    )
    manifest.retrieval_config_hash = hash_retrieval_config()

    # Scenario sets
    manifest.scenario_sets["tuning_dev"] = hash_scenario_set(tuning, "tuning_dev")
    manifest.scenario_sets["holdout"] = hash_scenario_set(holdout, "holdout")

    return manifest


def validate_and_attach_audit(manifest: EvalManifest) -> EvalManifest:
    """Run audit checks and attach results to manifest."""
    holdout = load_holdout_scenarios()
    mutation_log = MutationLog.load()
    audit_report = validate_mutation_integrity(holdout, mutation_log)
    manifest.audit = audit_report
    return manifest
