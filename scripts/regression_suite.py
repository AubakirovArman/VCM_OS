#!/usr/bin/env python3
"""CI Regression Suite — runs all evals and enforces metric gates."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.evals.scenarios.project_state_scenarios import load_project_state_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


# RC4 Metric Gates
GATES = {
    "holdout_restore": 0.80,
    "holdout_recall": 0.60,
    "holdout_token_avg": 120,
    "pso_score": 0.50,
    "decision_recall": 0.90,
    "error_recall": 0.50,
    "tests_passing": 80,
    "query_latency_ms": 200,
    "ingestion_rate": 5.0,
    "orphan_ratio": 0.40,
}


def run_pytest() -> tuple[int, int]:
    print("\n=== Running pytest ===")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    # Parse "N passed"
    passed = 0
    for line in result.stdout.splitlines():
        if "passed" in line:
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    passed = int(p)
                    break
    return passed, result.returncode


def run_holdout_eval() -> dict:
    print("\n=== Running Holdout Eval ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    scenarios = load_holdout_scenarios()
    scores = []
    recalls = []
    tokens = []
    for s in scenarios:
        runner.ingest_scenario(s)
        pack = runner.run_vcm(s)
        score = runner.score_pack(pack, s)
        scores.append(score.get("overall_restore", score.get("restore_score", 0)))
        recalls.append(score.get("overall_verbatim", score.get("recall_score", 0)))
        tokens.append(score.get("token_usage", score.get("tokens", 0)))

    import os
    os.unlink(db_path)

    return {
        "restore": sum(scores) / len(scores),
        "recall": sum(recalls) / len(recalls),
        "token_avg": sum(tokens) / len(tokens),
        "token_max": max(tokens),
    }


def run_component_eval() -> dict:
    print("\n=== Running Component Eval ===")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    pso_scenarios = load_project_state_scenarios()
    pso_scores = []
    for s in pso_scenarios:
        runner.ingest_scenario(s)
        pso = runner.pso_store.load(s.project_id)
        if pso:
            pack = runner.run_vcm(s, override_query=s.test_query)
            pack_text = " ".join(sec.content.lower() for sec in pack.sections)

            def _fuzzy(val: str) -> bool:
                if not val:
                    return False
                val_lower = val.lower()
                if val_lower in pack_text:
                    return True
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
            pso_scores.append(sum(checks.values()) / max(len(checks), 1))

    holdout = load_holdout_scenarios()
    dec_recalls = []
    err_recalls = []
    for s in holdout:
        runner.ingest_scenario(s)
        pack = runner.run_vcm(s, override_query=s.test_query)
        pack_text = " ".join(sec.content.lower() for sec in pack.sections)
        dec_recalls.append(sum(1 for d in s.expected_decisions if d.lower() in pack_text) / max(len(s.expected_decisions), 1))
        err_recalls.append(sum(1 for e in s.expected_errors if e.lower() in pack_text) / max(len(s.expected_errors), 1))

    import os
    os.unlink(db_path)

    return {
        "pso_score": sum(pso_scores) / len(pso_scores) if pso_scores else 0,
        "decision_recall": sum(dec_recalls) / len(dec_recalls),
        "error_recall": sum(err_recalls) / len(err_recalls),
    }


def run_load_test() -> dict:
    print("\n=== Running Load Test ===")
    result = subprocess.run(
        [sys.executable, "scripts/load_test.py", "--memories", "200", "--projects", "10", "--queries", "30", "--output", "/tmp/load_test.json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    print(result.stdout)
    try:
        with open("/tmp/load_test.json") as f:
            data = json.load(f)
        return {
            "query_latency_ms": data.get("query_avg_ms", 999),
            "ingestion_rate": data.get("ingestion_rate_mem_per_sec", 0),
            "orphan_ratio": data.get("orphan_ratio", 1.0),
        }
    except Exception:
        return {"query_latency_ms": 999, "ingestion_rate": 0}


def main():
    print("=" * 70)
    print("VCM OS RC4 Regression Suite")
    print("=" * 70)

    passed, pytest_rc = run_pytest()
    holdout = run_holdout_eval()
    components = run_component_eval()
    load = run_load_test()

    results = {
        "tests_passing": passed,
        "holdout_restore": holdout["restore"],
        "holdout_recall": holdout["recall"],
        "holdout_token_avg": holdout["token_avg"],
        "pso_score": components["pso_score"],
        "decision_recall": components["decision_recall"],
        "error_recall": components["error_recall"],
        "query_latency_ms": load["query_latency_ms"],
        "ingestion_rate": load["ingestion_rate"],
        "orphan_ratio": load.get("orphan_ratio", 1.0),
    }

    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)
    all_pass = True
    for key, value in results.items():
        gate = GATES.get(key)
        if gate is not None:
            if key in ("holdout_token_avg", "query_latency_ms", "orphan_ratio"):
                status = "PASS" if value <= gate else "FAIL"
            else:
                status = "PASS" if value >= gate else "FAIL"
            if status == "FAIL":
                all_pass = False
            print(f"  {key}: {value:.3f} (gate: {gate}) [{status}]")
        else:
            print(f"  {key}: {value:.3f}")

    if pytest_rc != 0:
        print("\npytest FAILED — some tests did not pass")
        all_pass = False

    with open("regression_results.json", "w") as f:
        json.dump({"results": results, "all_pass": all_pass}, f, indent=2)

    if all_pass:
        print("\n✅ All gates passed")
        sys.exit(0)
    else:
        print("\n❌ Some gates failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
