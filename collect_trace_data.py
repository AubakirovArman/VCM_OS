#!/usr/bin/env python3
"""Collect trace data from tuning eval for learned router training."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.loader import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


def collect_traces():
    store = SQLiteStore()
    vi = VectorIndex()
    si = SparseIndex()
    writer = MemoryWriter(store, vi, si)
    runner = ExperimentRunner(store, vi, si, writer)

    scenarios = load_all_scenarios()
    traces = []

    for sc in scenarios:
        runner.ingest_scenario(sc)
        pack = runner.run_vcm(sc)

        trace = pack.trace_log if hasattr(pack, "trace_log") else {}
        if trace:
            traces.append({
                "scenario": sc.name,
                "query": trace.get("query", ""),
                "events": trace.get("events", []),
                "drops": [
                    {"stage": e["stage"], "reason": e["details"].get("reason", "unknown")}
                    for e in trace.get("events", [])
                    if e["action"] == "dropped"
                ],
                "inclusions": [
                    {"stage": e["stage"], "memory_id": e["memory_id"]}
                    for e in trace.get("events", [])
                    if e["action"] == "included"
                ],
            })

    with open("trace_data.json", "w") as f:
        json.dump(traces, f, indent=2)

    print(f"Collected {len(traces)} traces")
    print(f"Total drops: {sum(len(t['drops']) for t in traces)}")
    print(f"Total inclusions: {sum(len(t['inclusions']) for t in traces)}")


if __name__ == "__main__":
    collect_traces()
