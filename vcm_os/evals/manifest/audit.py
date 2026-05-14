"""Manifest audit: frozen holdout validation and split purity checks."""
from typing import Dict, List, Set, Tuple

from vcm_os.evals.scenarios.types import EvalScenario


class ManifestAuditError(Exception):
    pass


def validate_frozen_inclusion(
    holdout_scenarios: List[EvalScenario],
    manifest_entries: List[Dict],
) -> Dict:
    """Verify all frozen scenarios are present and hashes match manifest."""
    errors = []
    manifest_ids = {e["name"]: e["hash"] for e in manifest_entries}
    run_ids = {sc.name for sc in holdout_scenarios}

    missing = set(manifest_ids.keys()) - run_ids
    if missing:
        errors.append(f"Missing frozen scenarios: {sorted(missing)}")

    extra = run_ids - set(manifest_ids.keys())
    if extra:
        errors.append(f"Extra scenarios not in manifest: {sorted(extra)}")

    locked_violations = [sc.name for sc in holdout_scenarios if not sc.locked]
    if locked_violations:
        errors.append(f"Unlocked holdout scenarios: {locked_violations}")

    return {
        "all_frozen_scenarios_ran": len(missing) == 0,
        "scenario_mutations_after_freeze": len(errors),
        "missing_scenarios": sorted(missing),
        "extra_scenarios": sorted(extra),
        "locked_violations": locked_violations,
        "errors": errors,
    }


def validate_split_purity(
    tuning_scenarios: List[EvalScenario],
    holdout_scenarios: List[EvalScenario],
) -> Dict:
    """Ensure no overlap between tuning and holdout sets."""
    tuning_names = {sc.name for sc in tuning_scenarios}
    holdout_names = {sc.name for sc in holdout_scenarios}
    overlap = tuning_names & holdout_names

    return {
        "split_purity_ok": len(overlap) == 0,
        "overlap_scenarios": sorted(overlap),
    }


def validate_scenario_hashes(
    scenarios: List[EvalScenario],
    expected_hashes: Dict[str, str],
) -> Dict:
    """Compare runtime scenario hashes against canonical manifest."""
    from vcm_os.evals.manifest.scenario_hasher import hash_scenario

    mismatches = []
    for sc in scenarios:
        actual = hash_scenario(sc)
        expected = expected_hashes.get(sc.name)
        if expected and actual != expected:
            mismatches.append({
                "name": sc.name,
                "expected": expected,
                "actual": actual,
            })

    return {
        "hashes_match": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def run_full_audit(
    tuning: List[EvalScenario],
    holdout: List[EvalScenario],
    manifest: "EvalManifest",
) -> Dict:
    """Run all audit checks and return combined report."""
    holdout_entry = manifest.scenario_sets.get("holdout", {})
    holdout_manifest_entries = holdout_entry.get("entries", [])

    inclusion = validate_frozen_inclusion(holdout, holdout_manifest_entries)
    purity = validate_split_purity(tuning, holdout)

    expected_hashes = {e["name"]: e["hash"] for e in holdout_manifest_entries}
    hash_check = validate_scenario_hashes(holdout, expected_hashes)

    all_ok = (
        inclusion["all_frozen_scenarios_ran"]
        and inclusion["scenario_mutations_after_freeze"] == 0
        and purity["split_purity_ok"]
        and hash_check["hashes_match"]
    )

    return {
        "audit_passed": all_ok,
        "inclusion": inclusion,
        "split_purity": purity,
        "hash_integrity": hash_check,
    }
