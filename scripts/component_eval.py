#!/usr/bin/env python3
"""Component-specific evaluation for PSO v2, Decision Ledger v2, Error Ledger v2."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.evals.scenarios.project_state_scenarios import load_project_state_scenarios
from vcm_os.evals.scenarios.v2_enriched_scenarios import load_v2_enriched_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


def eval_pso(runner, scenarios):
    """Evaluate PSO v2 field coverage."""
    results = []
    for s in scenarios:
        runner.ingest_scenario(s)
        pso = runner.pso_store.load(s.project_id)
        if not pso:
            results.append({"scenario": s.name, "found": False})
            continue

        pack = runner.run_vcm(s, override_query=s.test_query)
        pack_text = " ".join(sec.content.lower() for sec in pack.sections)

        def _fuzzy(val: str) -> bool:
            if not val:
                return False
            val_lower = val.lower()
            # If the full text is present, great
            if val_lower in pack_text:
                return True
            # Otherwise check for key words (length > 4)
            words = [w for w in val_lower.split() if len(w) > 4]
            return any(w in pack_text for w in words)

        checks = {
            "project_phase": _fuzzy(pso.project_phase),
            "current_branch": _fuzzy(pso.current_branch),
            "current_milestone": _fuzzy(pso.current_milestone),
            "test_status": _fuzzy(pso.test_status),
            "deployment_status": _fuzzy(pso.deployment_status),
            "blocked_tasks": any(_fuzzy(bt) for bt in pso.blocked_tasks),
            "active_experiments": any(_fuzzy(ex) for ex in pso.active_experiments),
            "risk_register": any(_fuzzy(r) for r in pso.risk_register),
        }

        results.append({
            "scenario": s.name,
            "found": True,
            "checks": checks,
            "score": sum(checks.values()) / max(len(checks), 1),
        })

    return results


def eval_decisions(runner, scenarios):
    """Evaluate Decision Ledger v2 coverage."""
    results = []
    for s in scenarios:
        runner.ingest_scenario(s)
        pack = runner.run_vcm(s, override_query=s.test_query)
        pack_text = " ".join(sec.content.lower() for sec in pack.sections)

        dec_recall = sum(1 for d in s.expected_decisions if d.lower() in pack_text) / max(len(s.expected_decisions), 1)

        # Check for v2 fields: rationale, alternatives, tradeoffs
        v2_fields = {"rationale": False, "alternatives": False, "tradeoffs": False}
        mems = runner.store.get_memories(project_id=s.project_id, memory_type="decision", limit=20)
        for m in mems:
            if m.decisions:
                for d in m.decisions:
                    if d.rationale:
                        v2_fields["rationale"] = True
                    if d.alternatives:
                        v2_fields["alternatives"] = True
                    if d.tradeoffs:
                        v2_fields["tradeoffs"] = True

        results.append({
            "scenario": s.name,
            "decision_recall": dec_recall,
            "v2_fields_present": v2_fields,
            "v2_score": sum(v2_fields.values()) / 3,
        })

    return results


def eval_errors(runner, scenarios):
    """Evaluate Error Ledger v2 coverage."""
    results = []
    for s in scenarios:
        runner.ingest_scenario(s)
        pack = runner.run_vcm(s, override_query=s.test_query)
        pack_text = " ".join(sec.content.lower() for sec in pack.sections)

        err_recall = sum(1 for e in s.expected_errors if e.lower() in pack_text) / max(len(s.expected_errors), 1)

        # Check for v2 fields: root_cause, fix_attempt, verified_fix, affected_files, recurrence_risk
        v2_fields = {"root_cause": False, "fix_attempt": False, "verified_fix": False, "affected_files": False, "recurrence_risk": False}
        mems = runner.store.get_memories(project_id=s.project_id, memory_type="error", limit=20)
        for m in mems:
            if m.errors_found:
                for e in m.errors_found:
                    if e.root_cause:
                        v2_fields["root_cause"] = True
                    if e.fix_attempt:
                        v2_fields["fix_attempt"] = True
                    if e.verified_fix:
                        v2_fields["verified_fix"] = True
                    if e.affected_files:
                        v2_fields["affected_files"] = True
                    if e.recurrence_risk > 0:
                        v2_fields["recurrence_risk"] = True

        results.append({
            "scenario": s.name,
            "error_recall": err_recall,
            "v2_fields_present": v2_fields,
            "v2_score": sum(v2_fields.values()) / 5,
        })

    return results


def eval_v2_fields(runner):
    """Evaluate v2 fields using enriched scenarios."""
    scenarios = load_v2_enriched_scenarios()
    dec_v2 = {"rationale": False, "alternatives": False, "tradeoffs": False}
    err_v2 = {"root_cause": False, "fix_attempt": False, "verified_fix": False, "affected_files": False, "recurrence_risk": False}

    for s in scenarios:
        runner.ingest_scenario(s)
        # Decision v2
        dec_mems = runner.store.get_memories(project_id=s.project_id, memory_type="decision", limit=20)
        for m in dec_mems:
            if m.decisions:
                for d in m.decisions:
                    if d.rationale:
                        dec_v2["rationale"] = True
                    if d.alternatives:
                        dec_v2["alternatives"] = True
                    if d.tradeoffs:
                        dec_v2["tradeoffs"] = True
        # Error v2
        err_mems = runner.store.get_memories(project_id=s.project_id, memory_type="error", limit=20)
        for m in err_mems:
            if m.errors_found:
                for e in m.errors_found:
                    if e.root_cause:
                        err_v2["root_cause"] = True
                    if e.fix_attempt:
                        err_v2["fix_attempt"] = True
                    if e.verified_fix:
                        err_v2["verified_fix"] = True
                    if e.affected_files:
                        err_v2["affected_files"] = True
                    if e.recurrence_risk > 0:
                        err_v2["recurrence_risk"] = True

    return {
        "decision_v2_score": sum(dec_v2.values()) / 3,
        "decision_v2_fields": dec_v2,
        "error_v2_score": sum(err_v2.values()) / 5,
        "error_v2_fields": err_v2,
    }


def main():
    parser = argparse.ArgumentParser(description="Component-specific evaluation")
    parser.add_argument("--output", type=str, default="component_eval_results.json", help="Output JSON file")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    print("=" * 70)
    print("Component-Specific Evaluation")
    print("=" * 70)

    # PSO eval
    print("\n--- PSO v2 Evaluation ---")
    pso_scenarios = load_project_state_scenarios()
    pso_results = eval_pso(runner, pso_scenarios)
    pso_scores = [r["score"] for r in pso_results if r.get("found")]
    print(f"PSO scenarios: {len(pso_results)}")
    print(f"Avg PSO score: {sum(pso_scores)/len(pso_scores):.3f}" if pso_scores else "N/A")
    for r in pso_results:
        print(f"  {r['scenario']}: score={r.get('score', 'N/A')}")

    # Decision eval
    print("\n--- Decision Ledger v2 Evaluation ---")
    holdout = load_holdout_scenarios()
    dec_results = eval_decisions(runner, holdout)
    dec_recalls = [r["decision_recall"] for r in dec_results]
    v2_scores = [r["v2_score"] for r in dec_results]
    print(f"Decision recall avg: {sum(dec_recalls)/len(dec_recalls):.3f}")
    print(f"Decision v2 fields avg: {sum(v2_scores)/len(v2_scores):.3f}")

    # Error eval
    print("\n--- Error Ledger v2 Evaluation ---")
    err_results = eval_errors(runner, holdout)
    err_recalls = [r["error_recall"] for r in err_results]
    v2_scores = [r["v2_score"] for r in err_results]
    print(f"Error recall avg: {sum(err_recalls)/len(err_recalls):.3f}")
    print(f"Error v2 fields avg: {sum(v2_scores)/len(v2_scores):.3f}")

    # V2 field eval
    print("\n--- v2 Field Evaluation (Enriched Scenarios) ---")
    v2_results = eval_v2_fields(runner)
    print(f"Decision v2 score: {v2_results['decision_v2_score']:.3f}")
    print(f"  Fields: {v2_results['decision_v2_fields']}")
    print(f"Error v2 score: {v2_results['error_v2_score']:.3f}")
    print(f"  Fields: {v2_results['error_v2_fields']}")

    results = {
        "pso": {"results": pso_results, "avg_score": sum(pso_scores)/len(pso_scores) if pso_scores else 0},
        "decisions": {"results": dec_results, "avg_recall": sum(dec_recalls)/len(dec_recalls), "avg_v2": sum([r['v2_score'] for r in dec_results])/len(dec_results)},
        "errors": {"results": err_results, "avg_recall": sum(err_recalls)/len(err_recalls), "avg_v2": sum([r['v2_score'] for r in err_results])/len(err_results)},
        "v2_enriched": v2_results,
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")

    import os
    os.unlink(db_path)


if __name__ == "__main__":
    main()
