"""Quick holdout diagnostic runner for v0.8 Exact Symbol Vault."""
import json
import tempfile
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_loader import load_holdout_scenarios
from vcm_os.evals.mutation_log import MutationLog
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def run_holdout():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = ExperimentRunner(store, vector_index, sparse_index, writer)

        holdout = load_holdout_scenarios()
        print(f"Loaded {len(holdout)} holdout scenarios")

        # Validate against mutation log
        log = MutationLog.load()
        validation = log.validate_against_run([s.name for s in holdout])
        print(f"Frozen validation: all_frozen_present={validation['all_frozen_present']}")
        if not validation["all_frozen_present"]:
            print(f"Missing: {validation['missing_from_run']}")
            print(f"Extra: {validation['extra_not_frozen']}")

        results = []
        for sc in holdout:
            runner.ingest_scenario(sc)
            pack = runner.run_vcm(sc)
            scores = runner.score_pack(pack, sc)
            results.append({
                "scenario": sc.name,
                **scores,
            })
            print(f"  {sc.name}: restore={scores['overall_restore']:.3f} "
                  f"tokens={scores['token_usage']} "
                  f"quality={scores['quality_v0_7']:.3f} "
                  f"stale={scores['stale_penalty']:.3f}")

        # Summary
        avg_restore = sum(r["overall_restore"] for r in results) / len(results)
        avg_tokens = sum(r["token_usage"] for r in results) / len(results)
        avg_quality = sum(r["quality_v0_7"] for r in results) / len(results)
        avg_stale = sum(r["stale_penalty"] for r in results) / len(results)

        print(f"\n=== HOLDOUT SUMMARY v0.8 ===")
        print(f"  avg_restore:   {avg_restore:.3f}")
        print(f"  avg_tokens:    {avg_tokens:.1f}")
        print(f"  avg_quality:   {avg_quality:.3f}")
        print(f"  avg_stale:     {avg_stale:.3f}")

        # Exact scenario detail
        exact = [r for r in results if "exact" in r["scenario"]]
        if exact:
            print(f"\n  Exact scenarios ({len(exact)}):")
            for r in exact:
                print(f"    {r['scenario']}: restore={r['overall_restore']:.3f} "
                      f"symbol_recall={r.get('exact_symbol_recall', 0):.3f}")

        with open("holdout_diagnostic_v0.8.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nSaved to holdout_diagnostic_v0.8.json")


if __name__ == "__main__":
    run_holdout()
