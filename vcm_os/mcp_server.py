"""VCM-OS MCP Server — expose memory tools via Model Context Protocol.

Tools:
    vcm_build_context   — build a memory pack for a query
    vcm_write_event     — ingest an event into memory
    vcm_verify_response — verify an assistant response
    vcm_search_memory   — search project memory
    vcm_correct_memory  — apply a correction to a memory
    vcm_get_project_state — get current project state
"""
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.memory.correction import CorrectionService, MemoryCorrection
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.verifier import ResponseVerifier

mcp = FastMCP("vcm-os")

# Global state (initialized on first use)
_store: Optional[SQLiteStore] = None
_vec: Optional[VectorIndex] = None
_sparse: Optional[SparseIndex] = None
_writer: Optional[MemoryWriter] = None
_runner: Optional[ExperimentRunner] = None
_verifier: Optional[ResponseVerifier] = None


def _enum_value(value: Any) -> Any:
    """Return the raw enum value while keeping plain strings unchanged."""
    return getattr(value, "value", value)


def _clip(text: str, limit: int = 500) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _init():
    global _store, _vec, _sparse, _writer, _runner, _verifier
    if _store is None:
        _store = SQLiteStore()
        _vec = VectorIndex()
        _sparse = SparseIndex()
        _writer = MemoryWriter(_store, _vec, _sparse)
        _runner = ExperimentRunner(_store, _vec, _sparse, _writer)
        _verifier = ResponseVerifier()


@mcp.tool()
def vcm_build_context(
    project_id: str,
    query: str,
    session_id: Optional[str] = None,
    task_type: str = "general",
    max_pack_tokens: int = 500,
) -> str:
    """Build a compact memory context pack for the given query."""
    _init()
    request = MemoryRequest(
        project_id=project_id,
        session_id=session_id,
        query=query,
        task_type=task_type,
        token_budget=8192,
        max_pack_tokens=max_pack_tokens,
    )
    plan = _runner.router.make_plan(request)
    candidates = _runner.reader.retrieve(request, plan)
    scored = _runner.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]
    pack = _runner.pack_builder.build(request, memories)

    sections = []
    for s in pack.sections:
        if s.content.strip():
            sections.append(f"[{s.section_name}]\n{s.content}")
    pack_text = "\n\n".join(sections)

    meta = {
        "pack_tokens": pack.token_estimate,
        "sufficiency": pack.sufficiency_score,
        "memories_included": len(pack.sections),
    }
    return f"{json.dumps(meta)}\n\n{pack_text}"


@mcp.tool()
def vcm_write_event(
    project_id: str,
    session_id: str,
    event_type: str,
    raw_text: str,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Write an event into the VCM memory store."""
    _init()
    event = EventRecord(
        project_id=project_id,
        session_id=session_id,
        event_type=event_type,
        payload=payload or {},
        raw_text=raw_text,
    )
    report = _writer.capture_event(event)
    _vec.save()
    _sparse.save()
    return json.dumps({
        "objects_written": report.objects_written,
        "objects_linked": report.objects_linked,
        "contradictions_found": report.contradictions_found,
        "ledgers_updated": report.ledgers_updated,
    })


@mcp.tool()
def vcm_verify_response(
    project_id: str,
    response_text: str,
    query: str,
    session_id: Optional[str] = None,
) -> str:
    """Verify an assistant response against project memory."""
    _init()
    request = MemoryRequest(
        project_id=project_id,
        session_id=session_id,
        query=query,
        task_type="general",
        token_budget=8192,
        max_pack_tokens=500,
    )
    plan = _runner.router.make_plan(request)
    candidates = _runner.reader.retrieve(request, plan)
    scored = _runner.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]
    pack = _runner.pack_builder.build(request, memories)

    result = _verifier.verify(response_text, pack, memories)
    return json.dumps({
        "passed": result["passed"],
        "score": result["score"],
        "violations": result.get("violations", []),
        "warnings": result.get("warnings", []),
    })


@mcp.tool()
def vcm_search_memory(
    project_id: str,
    query: str,
    limit: int = 10,
) -> str:
    """Search project memory for relevant entries."""
    _init()
    request = MemoryRequest(
        project_id=project_id,
        query=query,
        task_type="general",
        token_budget=8192,
        max_pack_tokens=500,
    )
    plan = _runner.router.make_plan(request)
    candidates = _runner.reader.retrieve(request, plan)
    scored = _runner.scorer.rerank(candidates, request)

    results = []
    for mem, score in scored[:limit]:
        text = (mem.raw_text or mem.compressed_summary or "")[:200]
        results.append({
            "memory_id": mem.memory_id,
            "type": _enum_value(mem.memory_type),
            "score": round(score, 3),
            "text": text,
        })
    return json.dumps({"results": results}, indent=2)


@mcp.tool()
def vcm_correct_memory(
    memory_id: str,
    action: str,
    reason: str = "",
) -> str:
    """Apply a correction to a memory (stale, incorrect, important, duplicate, pin, unpin, delete)."""
    _init()
    service = CorrectionService(_store)
    result = service.apply(MemoryCorrection(memory_id, action, reason))
    return json.dumps(result)


@mcp.tool()
def vcm_get_project_state(project_id: str) -> str:
    """Get the current state of a project (decisions, errors, active goals)."""
    _init()
    mems = _store.get_memories(project_id=project_id, limit=100)
    decisions = [m for m in mems if _enum_value(m.memory_type) == "decision"]
    errors = [m for m in mems if _enum_value(m.memory_type) == "error"]
    goals = [m for m in mems if _enum_value(m.memory_type) == "goal"]

    return json.dumps({
        "project_id": project_id,
        "total_memories": len(mems),
        "active_decisions": [
            {
                "id": m.memory_id,
                "text": _clip(
                    m.decisions[0].statement if getattr(m, "decisions", None)
                    else (m.raw_text or "")
                ),
            }
            for m in decisions if _enum_value(getattr(m, "validity", "active")) == "active"
        ],
        "recent_errors": [
            {"id": m.memory_id, "text": _clip(m.raw_text or "")}
            for m in errors[:5]
        ],
        "active_goals": [
            {"id": m.memory_id, "text": _clip(m.raw_text or "")}
            for m in goals[:5]
        ],
    }, indent=2)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
