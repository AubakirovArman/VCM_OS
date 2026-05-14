"""Trace hooks for pack builder."""
from typing import Dict, List

from vcm_os.context.trace.core import TraceLog
from vcm_os.schemas import MemoryObject


def trace_budget(
    log: TraceLog,
    allocation: Dict[str, int],
) -> None:
    log.add("pack_builder", "budget_allocated", details={
        "allocation": allocation,
    })


def trace_inclusion(
    log: TraceLog,
    memory_id: str,
    section: str,
    reason: str = "",
) -> None:
    log.add("pack_builder", "included", memory_id=memory_id, details={
        "section": section,
        "reason": reason or "scored_high",
    })


def trace_drop(
    log: TraceLog,
    memory_id: str,
    reason: str,
    details: Dict = None,
) -> None:
    log.add("pack_builder", "dropped", memory_id=memory_id, details={
        "reason": reason,
        **(details or {}),
    })


def trace_rescue(
    log: TraceLog,
    memory_id: str,
    term: str,
) -> None:
    log.add("rescue", "rescued", memory_id=memory_id, details={
        "missing_term": term,
    })


def trace_final(log: TraceLog, token_estimate: int, sufficiency: float) -> None:
    log.add("pack_builder", "finalized", details={
        "token_estimate": token_estimate,
        "sufficiency": sufficiency,
        "unexplained_drops": len(log.unexplained_drops()),
    })
