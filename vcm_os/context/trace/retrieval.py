"""Trace hooks for retrieval pipeline."""
from typing import List, Tuple

from vcm_os.context.trace.core import TraceLog
from vcm_os.schemas import MemoryObject, MemoryRequest, RetrievalPlan


def trace_router(log: TraceLog, request: MemoryRequest, plan: RetrievalPlan) -> None:
    log.add("router", "plan_created", details={
        "task_type": request.task_type,
        "query": request.query,
        "plan_needs": {
            "session": plan.needs_session,
            "project": plan.needs_project,
            "decisions": plan.needs_decisions,
            "errors": plan.needs_errors,
            "code": plan.needs_code,
            "graph": plan.needs_graph,
        },
    })


def trace_reader(
    log: TraceLog,
    candidates: List[MemoryObject],
    vector_count: int = 0,
    sparse_count: int = 0,
) -> None:
    log.add("reader", "retrieved", details={
        "total_candidates": len(candidates),
        "vector_count": vector_count,
        "sparse_count": sparse_count,
    })
    for mem in candidates:
        log.add("reader", "candidate", memory_id=mem.memory_id, details={
            "memory_type": mem.memory_type,
            "score": getattr(mem, "score", None),
        })


def trace_scorer(
    log: TraceLog,
    scored: List[Tuple[MemoryObject, float]],
    top_n: int = 50,
) -> None:
    log.add("scorer", "reranked", details={
        "total_scored": len(scored),
        "top_n": top_n,
    })
    for mem, score in scored[:top_n]:
        log.add("scorer", "ranked", memory_id=mem.memory_id, details={
            "score": score,
        })
