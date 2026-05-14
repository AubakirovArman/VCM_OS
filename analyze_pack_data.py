#!/usr/bin/env python3
"""Analyze pack data from tuning eval to build learned router rules.

Collects per-scenario data:
- query, task_type
- memories included/excluded by type
- restore score (success/failure)
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.loader import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


def analyze():
    store = SQLiteStore()
    vi = VectorIndex()
    si = SparseIndex()
    writer = MemoryWriter(store, vi, si)
    runner = ExperimentRunner(store, vi, si, writer)

    scenarios = load_all_scenarios()

    # Frequency tables
    task_success = defaultdict(lambda: {"success": 0, "total": 0})
    mem_type_success = defaultdict(lambda: {"success": 0, "total": 0})
    section_success = defaultdict(lambda: {"success": 0, "total": 0})

    per_scenario = []

    for sc in scenarios:
        runner.ingest_scenario(sc)

        # VCM pack
        pack = runner.run_vcm(sc)
        score = runner.score_pack(pack, sc)

        # Determine task_type from query
        from vcm_os.memory.router import MemoryRouter
        task = MemoryRouter().classify_task(sc.test_query)

        # Count included memories
        included_types = Counter()
        for sec in pack.sections:
            for mid in (sec.memory_ids or []):
                mem = store.get_memory(mid)
                if mem:
                    included_types[mem.memory_type] += 1

        # Count total candidates
        from vcm_os.schemas import MemoryRequest
        request = MemoryRequest(
            project_id=sc.project_id,
            query=sc.test_query,
            token_budget=32768,
        )
        from vcm_os.memory.router import MemoryRouter
        plan = MemoryRouter().make_plan(request)
        from vcm_os.memory.reader import MemoryReader
        reader = MemoryReader(store, vi, si)
        candidates = reader.retrieve(request, plan)
        total_types = Counter(m.memory_type for m in candidates)

        # Success: restore >= 0.67 (2/3 goals/decisions/errors found)
        success = score["overall_restore"] >= 0.67

        # Update frequencies
        task_success[task]["total"] += 1
        if success:
            task_success[task]["success"] += 1

        for mtype, count in included_types.items():
            mem_type_success[mtype]["total"] += count
            if success:
                mem_type_success[mtype]["success"] += count

        for sec in pack.sections:
            sname = sec.section_name
            section_success[sname]["total"] += 1
            if success:
                section_success[sname]["success"] += 1

        per_scenario.append({
            "name": sc.name,
            "task": str(task),
            "query": sc.test_query,
            "restore": score["overall_restore"],
            "tokens": score["token_usage"],
            "success": success,
            "included_types": dict(included_types),
            "total_types": dict(total_types),
            "sections_present": [s.section_name for s in pack.sections],
        })

    # Build learned rules
    rules = {}
    for task, data in task_success.items():
        rate = data["success"] / max(data["total"], 1)
        rules[str(task)] = {
            "success_rate": rate,
            "total_scenarios": data["total"],
        }

    mem_rules = {}
    for mtype, data in mem_type_success.items():
        rate = data["success"] / max(data["total"], 1)
        mem_rules[mtype] = {
            "success_rate": rate,
            "total_inclusions": data["total"],
        }

    sec_rules = {}
    for sname, data in section_success.items():
        rate = data["success"] / max(data["total"], 1)
        sec_rules[sname] = {
            "success_rate": rate,
            "total_occurrences": data["total"],
        }

    analysis = {
        "task_success_rates": rules,
        "memory_type_success_rates": mem_rules,
        "section_success_rates": sec_rules,
        "per_scenario": per_scenario,
    }

    with open("pack_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print("=" * 80)
    print("PACK ANALYSIS — Learned Router Data")
    print("=" * 80)
    print(f"\nTotal scenarios: {len(scenarios)}")
    print(f"Successes: {sum(1 for p in per_scenario if p['success'])}")
    print(f"Failures: {sum(1 for p in per_scenario if not p['success'])}")

    print("\n--- Task Success Rates ---")
    for task, data in sorted(rules.items(), key=lambda x: x[1]["success_rate"], reverse=True):
        print(f"  {task}: {data['success_rate']:.2f} ({data['total_scenarios']} scenarios)")

    print("\n--- Memory Type Success Rates ---")
    for mtype, data in sorted(mem_rules.items(), key=lambda x: x[1]["success_rate"], reverse=True):
        print(f"  {mtype}: {data['success_rate']:.2f} ({data['total_inclusions']} inclusions)")

    print("\n--- Section Success Rates ---")
    for sname, data in sorted(sec_rules.items(), key=lambda x: x[1]["success_rate"], reverse=True):
        print(f"  {sname}: {data['success_rate']:.2f} ({data['total_occurrences']} occurrences)")


if __name__ == "__main__":
    analyze()
