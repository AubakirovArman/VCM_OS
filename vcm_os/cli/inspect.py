#!/usr/bin/env python3
"""VCM-OS Audit & Debug Inspection CLI.

Usage:
    python -m vcm_os.cli.inspect project <project_id>
    python -m vcm_os.cli.inspect pso <project_id>
    python -m vcm_os.cli.inspect decisions <project_id> [--limit 20]
    python -m vcm_os.cli.inspect errors <project_id> [--limit 20]
    python -m vcm_os.cli.inspect symbols <project_id> [--limit 20]
    python -m vcm_os.cli.inspect sessions <project_id> [--limit 20]
    python -m vcm_os.cli.inspect stats
"""

import argparse
import sys
from collections import Counter, defaultdict

from vcm_os.memory.project_state.store import ProjectStateStore
from vcm_os.memory.symbol_vault.store import SymbolVaultStore
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.schemas import MemoryType, Validity


def _fmt_list(items, max_items=10):
    if not items:
        return "  (none)"
    lines = []
    for item in items[:max_items]:
        lines.append(f"  • {item}")
    if len(items) > max_items:
        lines.append(f"  ... and {len(items) - max_items} more")
    return "\n".join(lines)


def inspect_project(project_id: str, store: SQLiteStore):
    mems = store.get_memories(project_id=project_id, limit=1000)
    events = store.get_events(project_id=project_id, limit=1000)
    sessions = store.get_sessions(project_id=project_id)

    print("=" * 70)
    print(f"Project: {project_id}")
    print("=" * 70)
    print(f"\nTotal memories:   {len(mems)}")
    print(f"Total events:     {len(events)}")
    print(f"Total sessions:   {len(sessions)}")

    # Memory type breakdown
    type_counts = Counter(m.memory_type.value for m in mems)
    print("\nMemory types:")
    for t, c in type_counts.most_common():
        print(f"  {t:20}: {c}")

    # Validity breakdown
    validity_counts = Counter(m.validity.value for m in mems)
    print("\nValidity:")
    for v, c in validity_counts.most_common():
        print(f"  {v:20}: {c}")

    # Recent activity
    print("\nRecent events (last 5):")
    for ev in events[:5]:
        print(f"  {ev.timestamp.isoformat()}  {ev.event_type:20}  {ev.raw_text[:60] if ev.raw_text else ''}")

    # Sessions
    print("\nSessions:")
    for sess in sessions[:10]:
        print(f"  {sess.session_id}  {sess.status}  {sess.title or '(no title)'}")

    print("\n" + "=" * 70)


def inspect_pso(project_id: str, store: SQLiteStore):
    pso_store = ProjectStateStore(store)
    pso = pso_store.load(project_id)

    print("=" * 70)
    print(f"Project State Object: {project_id}")
    print("=" * 70)

    if not pso:
        print("\n  (no PSO found)")
        print("\n" + "=" * 70)
        return

    print(f"\nVersion:        {pso.version}")
    print(f"Updated at:     {pso.updated_at}")
    print(f"Project phase:  {pso.project_phase or '(unknown)'}")
    print(f"Current branch: {pso.current_branch or '(unknown)'}")
    print(f"Milestone:      {pso.current_milestone or '(unknown)'}")
    print(f"Test status:    {pso.test_status or '(unknown)'}")
    print(f"Deploy status:  {pso.deployment_status or '(unknown)'}")
    print(f"Confidence:     {pso.confidence:.2f}")

    print(f"\nActive goals ({len(pso.active_goals)}):")
    print(_fmt_list(pso.active_goals))

    print(f"\nOpen tasks ({len(pso.open_tasks)}):")
    print(_fmt_list(pso.open_tasks))

    print(f"\nLatest decisions ({len(pso.latest_decisions)}):")
    print(_fmt_list(pso.latest_decisions))

    print(f"\nRejected decisions ({len(pso.rejected_decisions)}):")
    print(_fmt_list(pso.rejected_decisions))

    print(f"\nCurrent bugs ({len(pso.current_bugs)}):")
    print(_fmt_list(pso.current_bugs))

    print(f"\nActive files ({len(pso.active_files)}):")
    print(_fmt_list(pso.active_files))

    print(f"\nRecently changed files ({len(pso.recently_changed_files)}):")
    print(_fmt_list(pso.recently_changed_files))

    print(f"\nBlocked tasks ({len(pso.blocked_tasks)}):")
    print(_fmt_list(pso.blocked_tasks))

    print(f"\nActive experiments ({len(pso.active_experiments)}):")
    print(_fmt_list(pso.active_experiments))

    print(f"\nRisk register ({len(pso.risk_register)}):")
    print(_fmt_list(pso.risk_register))

    print(f"\nDependencies ({len(pso.dependencies)}):")
    print(_fmt_list(pso.dependencies))

    print(f"\nConstraints ({len(pso.constraints)}):")
    print(_fmt_list(pso.constraints))

    print("\n" + "=" * 70)


def inspect_decisions(project_id: str, store: SQLiteStore, limit: int = 20):
    mems = store.get_memories(project_id=project_id, memory_type="decision", limit=limit)
    # Also get from decisions table
    decisions = store.get_decisions(project_id=project_id, limit=limit)

    print("=" * 70)
    print(f"Decisions: {project_id}")
    print("=" * 70)

    print(f"\nFrom memory_objects ({len(mems)}):")
    for m in mems:
        status = m.validity.value if m.validity else "?"
        stmt = (m.compressed_summary or m.raw_text or "")[:80]
        print(f"  [{status:12}] {m.memory_id}  {stmt}")

    print(f"\nFrom decisions table ({len(decisions)}):")
    for d in decisions:
        print(f"  [{d.status:12}] {d.decision_id}  conf={d.confidence:.2f}  {d.decision_text[:80]}")

    print("\n" + "=" * 70)


def inspect_errors(project_id: str, store: SQLiteStore, limit: int = 20):
    mems = store.get_memories(project_id=project_id, memory_type="error", limit=limit)
    errors = store.get_errors(project_id=project_id, limit=limit)

    print("=" * 70)
    print(f"Errors: {project_id}")
    print("=" * 70)

    print(f"\nFrom memory_objects ({len(mems)}):")
    for m in mems:
        status = m.validity.value if m.validity else "?"
        stmt = (m.compressed_summary or m.raw_text or "")[:80]
        print(f"  [{status:12}] {m.memory_id}  {stmt}")

    print(f"\nFrom errors table ({len(errors)}):")
    for e in errors:
        print(f"  [{e.status:12}] {e.error_id}  kind={e.error_kind}  {e.error_text[:80]}")

    print("\n" + "=" * 70)


def inspect_symbols(project_id: str, store: SQLiteStore, limit: int = 20):
    sv_store = SymbolVaultStore(store)
    entries = sv_store.all_for_project(project_id)

    print("=" * 70)
    print(f"Symbol Vault: {project_id}")
    print("=" * 70)

    print(f"\nTotal symbols: {len(entries)}")

    by_type = Counter(e.symbol_type for e in entries)
    print("\nBy type:")
    for t, c in by_type.most_common():
        print(f"  {t:20}: {c}")

    print(f"\nSymbols (first {limit}):")
    for e in entries[:limit]:
        print(f"  {e.symbol_type:15}  {e.symbol}")

    print("\n" + "=" * 70)


def inspect_sessions(project_id: str, store: SQLiteStore, limit: int = 20):
    sessions = store.get_sessions(project_id=project_id)

    print("=" * 70)
    print(f"Sessions: {project_id}")
    print("=" * 70)

    print(f"\nTotal sessions: {len(sessions)}")
    for sess in sessions[:limit]:
        print(f"\n  {sess.session_id}")
        print(f"    Title:     {sess.title or '(no title)'}")
        print(f"    Status:    {sess.status}")
        print(f"    Branch:    {sess.branch or '(none)'}")
        print(f"    Created:   {sess.created_at.isoformat()}")
        print(f"    Last active: {sess.last_active_at.isoformat()}")
        print(f"    Goals:     {sess.active_goal_ids}")

    print("\n" + "=" * 70)


def inspect_stats(store: SQLiteStore):
    stats = store.get_stats()

    print("=" * 70)
    print("VCM-OS Global Statistics")
    print("=" * 70)

    print(f"\nEvents:           {stats['events']}")
    print(f"Memories:         {stats['memories']}")
    print(f"Projects:         {stats['projects']}")
    print(f"Sessions:         {stats['sessions']}")
    print(f"Stale memories:   {stats['stale_memories']}")
    print(f"Superseded:       {stats['superseded_memories']}")
    print(f"DB size:          {stats['db_size_bytes'] / 1024 / 1024:.2f} MB")

    print("\nMemory types:")
    for t, c in sorted(stats["memory_types"].items(), key=lambda x: -x[1]):
        print(f"  {t:20}: {c}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="VCM-OS Audit & Debug Inspection")
    subparsers = parser.add_subparsers(dest="command", help="Inspection target")

    # project
    p_proj = subparsers.add_parser("project", help="Inspect project overview")
    p_proj.add_argument("project_id", type=str, help="Project ID")

    # pso
    p_pso = subparsers.add_parser("pso", help="Inspect Project State Object")
    p_pso.add_argument("project_id", type=str, help="Project ID")

    # decisions
    p_dec = subparsers.add_parser("decisions", help="Inspect decisions")
    p_dec.add_argument("project_id", type=str, help="Project ID")
    p_dec.add_argument("--limit", type=int, default=20, help="Max items to show")

    # errors
    p_err = subparsers.add_parser("errors", help="Inspect errors")
    p_err.add_argument("project_id", type=str, help="Project ID")
    p_err.add_argument("--limit", type=int, default=20, help="Max items to show")

    # symbols
    p_sym = subparsers.add_parser("symbols", help="Inspect symbol vault")
    p_sym.add_argument("project_id", type=str, help="Project ID")
    p_sym.add_argument("--limit", type=int, default=20, help="Max items to show")

    # sessions
    p_sess = subparsers.add_parser("sessions", help="Inspect sessions")
    p_sess.add_argument("project_id", type=str, help="Project ID")
    p_sess.add_argument("--limit", type=int, default=20, help="Max items to show")

    # stats
    subparsers.add_parser("stats", help="Global statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    store = SQLiteStore()

    if args.command == "project":
        inspect_project(args.project_id, store)
    elif args.command == "pso":
        inspect_pso(args.project_id, store)
    elif args.command == "decisions":
        inspect_decisions(args.project_id, store, args.limit)
    elif args.command == "errors":
        inspect_errors(args.project_id, store, args.limit)
    elif args.command == "symbols":
        inspect_symbols(args.project_id, store, args.limit)
    elif args.command == "sessions":
        inspect_sessions(args.project_id, store, args.limit)
    elif args.command == "stats":
        inspect_stats(store)


if __name__ == "__main__":
    main()
