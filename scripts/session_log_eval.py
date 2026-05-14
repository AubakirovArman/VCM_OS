#!/usr/bin/env python3
"""Real session-log evaluation harness.

Reads rich session logs (JSON lines) and evaluates VCM-OS restore.

Usage:
    python scripts/session_log_eval.py --log scripts/session_logs/example_auth_refactor.jsonl \
        --query "What is the current project state for auth refactor?" \
        --expected-goals "refactor auth system" \
        --expected-decisions "use httpOnly cookie for refresh token" "use mock OAuth for tests" \
        --expected-errors "OAuth integration tests failing"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, SourceType
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


def load_session_log(path: str):
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def run_session_log_eval(
    log_path: str,
    project_id: str,
    session_id: str,
    query: str,
    expected_goals: list,
    expected_decisions: list,
    expected_errors: list,
):
    print("=" * 70)
    print("Real Session-Log Evaluation")
    print("=" * 70)

    events = load_session_log(log_path)
    print(f"\nLoaded {len(events)} events from {log_path}")

    import tempfile, os, time
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    # Ingest events
    for i, ev in enumerate(events):
        event = EventRecord(
            event_id=f"evt_{session_id}_{i:03d}",
            project_id=project_id,
            session_id=session_id,
            event_type=ev["event_type"],
            raw_text=ev.get("raw_text", ""),
            payload={
                "content": ev.get("raw_text", ""),
                "tool_name": ev.get("tool_name", ""),
                "file_path": ev.get("file_path", ""),
            },
            source_type=SourceType.USER_MESSAGE,
        )
        writer.capture_event(event)

    # Build query and run directly
    from vcm_os.schemas import MemoryRequest
    request = MemoryRequest(
        project_id=project_id,
        query=query,
        required_terms=expected_decisions + expected_goals + expected_errors,
    )

    plan = runner.router.make_plan(request)
    candidates = runner.reader.retrieve(request, plan)
    scored = runner.scorer.rerank(candidates, request)
    pack = runner.pack_builder.build(request, [m for m, _ in scored[:50]])

    # Score
    from vcm_os.evals.metrics import evaluate_session_restore
    score = evaluate_session_restore(pack, expected_goals, expected_decisions, expected_errors)

    text = " ".join(s.content.lower() for s in pack.sections)
    keyword_hits = sum(1 for kw in expected_goals + expected_decisions + expected_errors if kw.lower() in text)
    keyword_total = len(expected_goals) + len(expected_decisions) + len(expected_errors)

    print(f"\n--- Results ---")
    print(f"Query: {query}")
    print(f"Overall restore: {score['overall']:.3f}")
    print(f"Goal recall:     {score['goal_recall']:.3f}")
    print(f"Decision recall: {score['decision_recall']:.3f}")
    print(f"Error recall:    {score['error_recall']:.3f}")
    print(f"Keyword hits:    {keyword_hits}/{keyword_total}")
    print(f"Tokens:          {sum(s.token_estimate for s in pack.sections)}")

    print(f"\n--- Pack Sections ---")
    for s in pack.sections:
        if s.token_estimate > 0:
            print(f"  [{s.section_name:20}] {s.token_estimate:3}t: {s.content[:120]}")

    print("=" * 70)
    os.unlink(db_path)
    return score


def main():
    parser = argparse.ArgumentParser(description="Real Session-Log Evaluation")
    parser.add_argument("--log", type=str, required=True, help="Path to JSONL session log")
    parser.add_argument("--project-id", type=str, default="proj_session_eval", help="Project ID")
    parser.add_argument("--session-id", type=str, default="sess_eval_001", help="Session ID")
    parser.add_argument("--query", type=str, required=True, help="Test query")
    parser.add_argument("--expected-goals", nargs="+", default=[], help="Expected goals")
    parser.add_argument("--expected-decisions", nargs="+", default=[], help="Expected decisions")
    parser.add_argument("--expected-errors", nargs="+", default=[], help="Expected errors")
    args = parser.parse_args()

    run_session_log_eval(
        log_path=args.log,
        project_id=args.project_id,
        session_id=args.session_id,
        query=args.query,
        expected_goals=args.expected_goals,
        expected_decisions=args.expected_decisions,
        expected_errors=args.expected_errors,
    )


if __name__ == "__main__":
    main()
