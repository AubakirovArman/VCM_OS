#!/usr/bin/env python3
"""VCM-OS Memory Diagnostics CLI.

Usage:
    python -m vcm_os.cli.diagnose --project proj_auth
    python -m vcm_os.cli.diagnose --scenario exact_config_key
"""

import argparse
import sys
from collections import defaultdict

from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Memory Diagnostics")
    parser.add_argument("--project", type=str, help="Project ID")
    parser.add_argument("--scenario", type=str, help="Scenario name")
    args = parser.parse_args()

    project_id = args.project
    if args.scenario:
        scenarios = load_all_scenarios()
        scenario = next((s for s in scenarios if s.name == args.scenario), None)
        if not scenario:
            print(f"Scenario '{args.scenario}' not found.")
            sys.exit(1)
        project_id = scenario.project_id

    if not project_id:
        parser.print_help()
        sys.exit(1)

    store = SQLiteStore()
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    # Ingest scenario if specified
    if args.scenario:
        from vcm_os.evals.experiments import ExperimentRunner
        runner = ExperimentRunner(store, vec, sparse, writer)
        runner.ingest_scenario(scenario)

    mems = store.get_memories(project_id=project_id, limit=500)

    print("=" * 70)
    print(f"Memory Diagnostics for project: {project_id}")
    print("=" * 70)

    # 1. Total counts
    print(f"\nTotal memories: {len(mems)}")

    # 2. By type
    by_type = defaultdict(int)
    for m in mems:
        by_type[m.memory_type.value] += 1
    print("\nBy type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:15}: {c}")

    # 3. Duplicate analysis
    print("\nDuplicate analysis (normalized raw_text):")
    text_map = defaultdict(list)
    for m in mems:
        norm = " ".join((m.raw_text or "").strip().lower().split())
        text_map[norm].append(m)

    duplicates = 0
    dup_details = []
    for norm, group in text_map.items():
        if len(group) > 1:
            types = [m.memory_type.value for m in group]
            dup_details.append((norm[:80], len(group), types, [m.memory_id for m in group]))
            duplicates += len(group) - 1

    print(f"  Unique raw_texts: {len(text_map)}")
    print(f"  Duplicate instances: {duplicates}")
    if dup_details:
        print(f"  Top duplicates:")
        for text, count, types, ids in sorted(dup_details, key=lambda x: -x[1])[:10]:
            print(f"    Count={count} types={types} ids={ids}")
            print(f"    Text: {text}...")
    else:
        print("  No duplicates found.")

    # 4. Per-event memory count
    print("\nPer-event memory count:")
    event_map = defaultdict(list)
    for m in mems:
        if m.source_pointer and m.source_pointer.event_id:
            event_map[m.source_pointer.event_id].append(m.memory_type.value)
    multi_mem_events = {e: types for e, types in event_map.items() if len(types) > 1}
    print(f"  Events with >1 memory: {len(multi_mem_events)}")
    for eid, types in sorted(multi_mem_events.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"    {eid}: {types}")

    # 5. Store canonicalization skips
    print(f"\nCanonicalization skips: {getattr(writer, '_last_skip_count', 'N/A (run eval first)')}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
