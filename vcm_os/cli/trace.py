#!/usr/bin/env python3
"""VCM-OS Retrieval & Pack Trace CLI.

Usage:
    python -m vcm_os.cli.trace --scenario search_optimization_regression
    python -m vcm_os.cli.trace --project proj_auth --query "How do I fix the auth refresh loop?"
    python -m vcm_os.cli.trace --scenario exact_config_key --show vector,sparse,pack
"""

import argparse
import sys
from typing import List, Optional

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.schemas import MemoryRequest


class TraceViewer:
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner

    def trace(
        self,
        scenario=None,
        project_id: Optional[str] = None,
        query: Optional[str] = None,
        show: List[str] = None,
    ) -> str:
        show = show or ["vector", "sparse", "hybrid", "dedup", "budget", "pack", "gold"]
        lines = []
        lines.append("=" * 70)
        lines.append("VCM-OS Retrieval & Pack Trace")
        lines.append("=" * 70)

        if scenario:
            self.runner.ingest_scenario(scenario)
            request = MemoryRequest(
                project_id=scenario.project_id,
                query=scenario.test_query,
                required_terms=list(scenario.critical_gold) + list(scenario.protected_terms),
            )
            lines.append(f"Scenario:      {scenario.name}")
            lines.append(f"Project:       {scenario.project_id}")
            lines.append(f"Query:         {scenario.test_query}")
            lines.append(f"Required terms: {request.required_terms}")
        else:
            request = MemoryRequest(project_id=project_id, query=query)
            lines.append(f"Project:       {project_id}")
            lines.append(f"Query:         {query}")

        lines.append("")

        # 1. Vector retrieval
        if "vector" in show:
            lines.append("--- Vector Top-10 ---")
            vec_results = self.runner.vector_index.search(request.query, top_k=10)
            for i, (mid, score) in enumerate(vec_results, 1):
                mem = self.runner.store.get_memory(mid)
                if mem:
                    lines.append(f"  {i:2}. [{mem.memory_type.value:12}] score={score:.3f} {mem.compressed_summary[:80]}")
            lines.append("")

        # 2. Sparse retrieval
        if "sparse" in show:
            lines.append("--- Sparse Top-10 ---")
            sparse_results = self.runner.sparse_index.search(request.query, top_k=10)
            for i, (mid, score) in enumerate(sparse_results, 1):
                mem = self.runner.store.get_memory(mid)
                if mem:
                    lines.append(f"  {i:2}. [{mem.memory_type.value:12}] score={score:.3f} {mem.compressed_summary[:80]}")
            lines.append("")

        # 3. Hybrid / RRF
        if "hybrid" in show:
            lines.append("--- Hybrid (RRF) Top-10 ---")
            plan = self.runner.router.make_plan(request)
            candidates = self.runner.reader.retrieve(request, plan)
            scored = self.runner.scorer.rerank(candidates, request)
            for i, (mem, score) in enumerate(scored[:10], 1):
                lines.append(f"  {i:2}. [{mem.memory_type.value:12}] score={score:.3f} {mem.compressed_summary[:80]}")
            lines.append("")

        # 4. Pack builder trace
        pack = self.runner.pack_builder.build(request, [m for m, _ in scored[:50]])

        if "dedup" in show:
            lines.append("--- Pack Builder: Deduplication ---")
            # Show what was dropped by dedup/budget
            seen_ids_flat = set()
            for s in pack.sections:
                seen_ids_flat.update(s.memory_ids)
            dropped = [m for m, _ in scored[:50] if m.memory_id not in seen_ids_flat]
            lines.append(f"  Included: {len(seen_ids_flat)} / {len(scored[:50])} candidates")
            lines.append(f"  Dropped by dedup/budget:")
            for m in dropped[:10]:
                lines.append(f"    - [{m.memory_type.value}] {m.compressed_summary[:60]}...")
            lines.append("")

        if "budget" in show:
            lines.append("--- Pack Builder: Budget ---")
            total = sum(s.token_estimate for s in pack.sections)
            for s in pack.sections:
                if s.token_estimate > 0:
                    lines.append(f"  [{s.section_name:20}] {s.token_estimate:4} tokens | {len(s.memory_ids)} items")
            lines.append(f"  {'TOTAL':20} {total:4} tokens")
            lines.append("")

        if "pack" in show:
            lines.append("--- Final Pack Content ---")
            for s in pack.sections:
                if s.token_estimate > 0:
                    lines.append(f"\n>> {s.section_name} ({s.token_estimate} tokens):")
                    lines.append(f"   {s.content[:300]}")
            lines.append("")

        # 5. Gold analysis
        if "gold" in show and scenario:
            lines.append("--- Gold Analysis ---")
            text = " ".join(s.content.lower() for s in pack.sections)

            for goal in scenario.expected_goals:
                hit = goal.lower() in text
                lines.append(f"  Goal '{goal[:40]}': {'✓' if hit else '✗ MISSING'}")
            for dec in scenario.expected_decisions:
                hit = dec.lower() in text
                lines.append(f"  Decision '{dec[:40]}': {'✓' if hit else '✗ MISSING'}")
            for err in scenario.expected_errors:
                hit = err.lower() in text
                lines.append(f"  Error '{err[:40]}': {'✓' if hit else '✗ MISSING'}")
            for kw in scenario.expected_answer_keywords:
                hit = kw.lower() in text
                lines.append(f"  Keyword '{kw}': {'✓' if hit else '✗ MISSING'}")
            for term in scenario.critical_gold:
                hit = term.lower() in text
                lines.append(f"  CRITICAL '{term}': {'✓' if hit else '✗ MISSING'}")
            lines.append("")

            score = self.runner.score_pack(pack, scenario)
            lines.append(f"  Overall restore:     {score['overall_restore']:.3f}")
            lines.append(f"  Keyword coverage:    {score['keyword_coverage']:.3f}")
            lines.append(f"  Critical survival:   {score.get('critical_survival', 'N/A')}")
            lines.append(f"  Protected survival:  {score.get('protected_survival', 'N/A')}")
            lines.append(f"  Quality score:       {score['quality_score']:.3f}")
            lines.append(f"  Token usage:         {score['token_usage']}")

        lines.append("=" * 70)
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Retrieval & Pack Trace")
    parser.add_argument("--scenario", type=str, help="Scenario name from synthetic benchmark")
    parser.add_argument("--project", type=str, help="Project ID (for ad-hoc trace)")
    parser.add_argument("--query", type=str, help="Query string (for ad-hoc trace)")
    parser.add_argument("--show", type=str, default="vector,sparse,hybrid,dedup,budget,pack,gold",
                        help="Comma-separated sections to show")
    args = parser.parse_args()

    show = [s.strip() for s in args.show.split(",")]

    scenario = None
    if args.scenario:
        scenarios = load_all_scenarios()
        scenario = next((s for s in scenarios if s.name == args.scenario), None)
        if not scenario:
            print(f"Scenario '{args.scenario}' not found. Available:")
            for s in scenarios:
                print(f"  - {s.name}")
            sys.exit(1)
        project_id = scenario.project_id
        query = scenario.test_query
    else:
        project_id = args.project
        query = args.query
        if not project_id or not query:
            parser.print_help()
            sys.exit(1)

    store = SQLiteStore()
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    viewer = TraceViewer(runner)
    output = viewer.trace(scenario=scenario, project_id=project_id, query=query, show=show)
    print(output)


if __name__ == "__main__":
    main()
