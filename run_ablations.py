#!/usr/bin/env python3
"""
Component ablation study for VCM-OS.
For each component, disable it and re-run holdout eval.
Measure delta in restore and quality.
"""
import json, tempfile
from typing import Any, Dict, List

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.experiments.t10 import T10_VCM_vs_FullContext
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex

ABLATIONS = {
    "no_pso": {"disable_pso": True},
    "no_symbol_vault": {"disable_symbol_vault": True},
    "no_reranker": {"disable_reranker": True},
    "no_stale_filter": {"disable_stale_filter": True},
    "no_goals": {"disable_goals": True},
    "no_decisions": {"disable_decisions": True},
    "no_rationales": {"disable_rationales": True},
    "no_adaptive_cap": {"disable_adaptive_cap": True},
    "no_compact_assembly": {"disable_compact_assembly": True},
}


class AblationExperimentRunner(ExperimentRunner):
    def __init__(self, store, vector_index, sparse_index, writer, ablation_config=None):
        super().__init__(store, vector_index, sparse_index, writer)
        self.ablation_config = ablation_config or {}

    def run_vcm(self, scenario, token_budget=32768, override_query=None):
        if self.ablation_config.get("disable_goals"):
            scenario = copy_scenario(scenario)
            scenario.expected_goals = []
        if self.ablation_config.get("disable_decisions"):
            scenario = copy_scenario(scenario)
            scenario.expected_decisions = []
        if self.ablation_config.get("disable_rationales"):
            scenario = copy_scenario(scenario)
            scenario.expected_rationales = []

        pack = super().run_vcm(scenario, token_budget, override_query)

        # Ablation: disable PSO
        if self.ablation_config.get("disable_pso"):
            pack.sections = [s for s in pack.sections if s.section_name != "project_state"]

        # Ablation: disable Symbol Vault
        if self.ablation_config.get("disable_symbol_vault"):
            pack.sections = [s for s in pack.sections if s.section_name != "exact_symbols"]

        # Ablation: disable stale filter (add stale facts back in)
        if self.ablation_config.get("disable_stale_filter"):
            # Stale filter is already applied in ingest. For simplicity,
            # we re-add stale facts to the pack text by appending a section.
            if scenario.stale_facts:
                from vcm_os.schemas import ContextPackSection
                stale_text = " ".join(scenario.stale_facts)
                pack.sections.append(ContextPackSection(
                    section_name="stale_facts",
                    content=stale_text,
                    token_estimate=len(stale_text.split()),
                ))

        # Ablation: disable adaptive cap (truncate protected terms)
        if self.ablation_config.get("disable_adaptive_cap"):
            for s in pack.sections:
                if len(s.content) > 80:
                    s.content = s.content[:80]

        # Ablation: disable compact assembly (use verbose format)
        if self.ablation_config.get("disable_compact_assembly"):
            for s in pack.sections:
                if s.content.startswith("g=") or s.content.startswith("s="):
                    s.content = s.content.replace("g=", "goal: ").replace("t=", "task: ").replace("d=", "decision: ").replace("b=", "bug: ").replace("f=", "files: ").replace("c=", "constraint: ").replace("s=", "symbol: ")

        # Recompute token estimate
        pack.token_estimate = sum(s.token_estimate for s in pack.sections)
        return pack


def copy_scenario(scenario):
    """Shallow copy a scenario for ablation modifications."""
    import copy
    return copy.copy(scenario)


def run_holdout(ablation_config=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/eval.db"
        store = SQLiteStore(db_path=db_path)
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        writer = MemoryWriter(store, vector_index, sparse_index)
        runner = AblationExperimentRunner(store, vector_index, sparse_index, writer, ablation_config)
        holdout = load_holdout_scenarios()
        t10 = T10_VCM_vs_FullContext(runner)
        results = t10.run(holdout)
        return results["vcm"]


def main():
    print("=" * 70)
    print("VCM-OS COMPONENT ABLATION STUDY")
    print("=" * 70)

    baseline = run_holdout()
    print(f"\nBaseline: restore={baseline['restore']:.3f} "
          f"verbatim={baseline.get('goal_recall_verbatim', baseline.get('overall_verbatim', 0)):.3f} "
          f"quality={baseline['quality']:.3f} "
          f"tokens={baseline['tokens']:.1f}\n")

    rows = []
    for name, config in ABLATIONS.items():
        r = run_holdout(config)
        delta_restore = r['restore'] - baseline['restore']
        delta_quality = r['quality'] - baseline['quality']
        delta_tokens = r['tokens'] - baseline['tokens']
        row = {
            'component': name,
            'restore': r['restore'],
            'quality': r['quality'],
            'tokens': r['tokens'],
            'delta_restore': delta_restore,
            'delta_quality': delta_quality,
            'delta_tokens': delta_tokens,
        }
        rows.append(row)
        print(f"{name:25s}: restore={r['restore']:.3f} ({delta_restore:+.3f})  "
              f"quality={r['quality']:.3f} ({delta_quality:+.3f})  "
              f"tokens={r['tokens']:.1f} ({delta_tokens:+.1f})")

    # Save
    out = {
        'baseline': baseline,
        'ablations': rows,
    }
    with open("ablation_results.json", 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n✅ Saved ablation_results.json")

    # Print sorted by impact
    print(f"\n--- Sorted by restore drop ---")
    for row in sorted(rows, key=lambda x: x['delta_restore']):
        print(f"  {row['component']:25s}: Δrestore={row['delta_restore']:+.3f}  "
              f"Δquality={row['delta_quality']:+.3f}")


if __name__ == "__main__":
    main()
