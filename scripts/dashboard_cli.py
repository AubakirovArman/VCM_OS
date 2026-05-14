#!/usr/bin/env python3
"""CLI dashboard for VCM-OS — real-time monitoring in terminal."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.dashboard.metrics import DashboardMetrics
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def print_dashboard(data: dict, watch: bool = False):
    """Print formatted dashboard."""
    health = data.get("health", {})
    latency = data.get("latency", {})
    retrieval = data.get("retrieval", {})
    errors = data.get("errors", {})

    if watch:
        print("\033[2J\033[H", end="")  # Clear screen

    print("=" * 70)
    print(f"VCM-OS Dashboard  v{data.get('version', '0.5.0')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print("=" * 70)

    # Health
    print("\n📊 HEALTH")
    print("-" * 40)
    basic = health.get("basic", {})
    print(f"  Memories:     {basic.get('memories', 0)}")
    print(f"  Events:       {basic.get('events', 0)}")
    print(f"  Projects:     {basic.get('projects', 0)}")
    print(f"  Sessions:     {basic.get('sessions', 0)}")
    print(f"  Health Score: {health.get('score', 0):.2f}")

    ages = health.get("ages", {})
    print(f"  Avg Age:      {ages.get('avg_days', 0):.1f} days")

    orphans = health.get("orphans", {})
    print(f"  Orphans:      {orphans.get('ratio', 0)*100:.1f}%")

    # Latency
    print("\n⚡ LATENCY & THROUGHPUT")
    print("-" * 40)
    print(f"  Events (1h):  {latency.get('recent_events_1h', 0)}")
    print(f"  Memories (1h): {latency.get('recent_memories_1h', 0)}")
    print(f"  Vector Index: {latency.get('vector_index_size', 0)} entries")
    print(f"  Sparse Index: {latency.get('sparse_index_size', 0)} entries")

    # Retrieval
    print("\n🔍 RETRIEVAL")
    print("-" * 40)
    print(f"  Total Memories: {retrieval.get('total_memories', 0)}")
    print(f"  Linked:         {retrieval.get('linked_memories', 0)}")
    print(f"  Link Ratio:     {retrieval.get('link_ratio', 0)*100:.1f}%")
    print("  By Type:")
    for t, c in retrieval.get("by_type", {}).items():
        print(f"    {t:12s}: {c}")

    # Errors
    print("\n⚠️  ERRORS & CORRECTIONS")
    print("-" * 40)
    print(f"  Recent Errors (24h): {errors.get('recent_errors_24h', 0)}")
    print(f"  Disputed:            {errors.get('disputed_memories', 0)}")
    print(f"  Stale:               {errors.get('stale_memories', 0)}")
    print(f"  Total Corrections:   {errors.get('total_corrections', 0)}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Dashboard CLI")
    parser.add_argument("--db", type=str, default=None, help="Database path")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh every 5s")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    from vcm_os.config import DB_PATH
    db_path = args.db or DB_PATH
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    metrics = DashboardMetrics(store, vec, sparse)

    while True:
        data = metrics.snapshot()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print_dashboard(data, watch=args.watch)

        if not args.watch:
            break
        time.sleep(5)


if __name__ == "__main__":
    main()
