import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from vcm_os.evals.experiments import (
    ExperimentRunner,
    F03_HybridRetrieval,
    H03_ProjectSwitching,
    I01_ProjectStateRestore,
    S05_FalseMemory,
    T10_VCM_vs_FullContext,
)
from vcm_os.evals.manifest_builder import build_manifest, validate_and_attach_audit
from vcm_os.evals.reports.report import generate_report
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.evals.scenarios.adversarial_symbols import load_adversarial_scenarios
from vcm_os.evals.scenarios.adversarial_hard import load_adversarial_hard_scenarios
from vcm_os.evals.scenarios.real_codebase import load_real_codebase_scenarios
from vcm_os.evals.scenarios.realistic_multi_repo import load_realistic_multi_repo_scenarios
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


class BenchmarkRunner:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.store = SQLiteStore(db_path=db_path)
        self.vector_index = VectorIndex()
        self.sparse_index = SparseIndex()
        self.writer = MemoryWriter(self.store, self.vector_index, self.sparse_index)
        self.experiment_runner = ExperimentRunner(
            self.store, self.vector_index, self.sparse_index, self.writer
        )

    def run_all(self) -> Dict:
        # Build canonical manifest before any eval work
        manifest = build_manifest()
        manifest = validate_and_attach_audit(manifest)
        if not manifest.audit.get("audit_passed", False):
            raise RuntimeError(
                f"Manifest audit failed: {manifest.audit}"
            )
        manifest_path = "eval_manifest.json"
        manifest.save(manifest_path)
        print(f"Canonical manifest saved to {manifest_path}")

        scenarios = load_all_scenarios()
        adversarial = load_adversarial_scenarios()
        real = load_real_codebase_scenarios()
        holdout = load_holdout_scenarios()
        print(f"Loaded {len(scenarios)} tuning scenarios")
        print(f"Loaded {len(adversarial)} adversarial scenarios")
        print(f"Loaded {len(real)} real codebase scenarios")
        print(f"Loaded {len(holdout)} holdout scenarios")

        # Separate H03 triple and S05
        normal_scenarios = [s for s in scenarios if not s.name.startswith("h03_") and s.name != "false_memory_s05"]
        h03_scenarios = [s for s in scenarios if s.name.startswith("h03_")]
        s05_scenario = next((s for s in scenarios if s.name == "false_memory_s05"), None)

        results = {}

        # T10: VCM vs baselines
        print("\n=== Running T10: VCM vs Full Context ===")
        t10 = T10_VCM_vs_FullContext(self.experiment_runner)
        results["T10"] = t10.run(normal_scenarios)

        # H03: Project switching
        if len(h03_scenarios) >= 3:
            print("\n=== Running H03: Project Switching ===")
            h03 = H03_ProjectSwitching(self.experiment_runner)
            results["H03"] = h03.run(h03_scenarios)

        # S05: False memory
        if s05_scenario:
            print("\n=== Running S05: False Memory Insertion ===")
            s05 = S05_FalseMemory(self.experiment_runner)
            results["S05"] = s05.run(s05_scenario)

        # F03: Hybrid retrieval (include superseded + exact-symbol scenarios)
        print("\n=== Running F03: Hybrid Retrieval ===")
        f03 = F03_HybridRetrieval(self.experiment_runner)
        f03_results = []
        f03_scenarios = normal_scenarios[:3]
        # Add superseded and exact-symbol scenarios if present
        for name in ["superseded_decision", "exact_config_key", "exact_api_endpoint", "exact_cicd_job", "exact_cve"]:
            sc = next((s for s in normal_scenarios if s.name == name), None)
            if sc:
                f03_scenarios.append(sc)
        for sc in f03_scenarios[:8]:
            f03_results.append(f03.run(sc))
        results["F03"] = f03_results

        # I01: Project state restore (sample 5 scenarios)
        print("\n=== Running I01: Project State Restore ===")
        i01 = I01_ProjectStateRestore(self.experiment_runner)
        i01_results = []
        for sc in normal_scenarios[:5]:
            i01_results.append(i01.run(sc))
        results["I01"] = i01_results

        # Adversarial
        print("\n=== Running Adversarial Scenarios ===")
        results["adversarial"] = t10.run(adversarial)

        # Adversarial Hard (20+ distractors)
        adversarial_hard = load_adversarial_hard_scenarios()
        print(f"\n=== Running Adversarial Hard Scenarios ({len(adversarial_hard)} scenarios, 20+ distractors) ===")
        results["adversarial_hard"] = t10.run(adversarial_hard)

        # Real codebase
        print("\n=== Running Real Codebase Scenarios ===")
        results["real_codebase"] = t10.run(real)

        # Realistic multi-repo
        multi_repo = load_realistic_multi_repo_scenarios()
        print(f"\n=== Running Realistic Multi-Repo Scenarios ({len(multi_repo)} scenarios) ===")
        results["multi_repo"] = t10.run(multi_repo)

        # Holdout
        print("\n=== Running Holdout Scenarios (FROZEN) ===")
        results["holdout"] = t10.run(holdout)

        return results

    def save_results(self, results: Dict, output_path: str = "eval_results.json"):
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {output_path}")


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        runner = BenchmarkRunner(db_path=db_path)
        results = runner.run_all()
        runner.save_results(results, "eval_results.json")
        generate_report(results)


if __name__ == "__main__":
    main()
