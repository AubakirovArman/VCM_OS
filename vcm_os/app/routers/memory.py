from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

import vcm_os.app.state as state
from vcm_os.app.models import CorrectionIn, EventIn, GraphExpandIn, MemoryReadIn, ReflectIn, DecayIn, StaleCheckIn
from vcm_os.schemas import MemoryObject, MemoryRequest

router = APIRouter()


@router.post("/memory/write")
async def memory_write(event_in: EventIn):
    from vcm_os.schemas import EventRecord
    event = EventRecord(
        session_id=event_in.session_id,
        project_id=event_in.project_id,
        event_type=event_in.event_type,
        payload=event_in.payload,
        raw_text=event_in.raw_text,
    )
    if event_in.use_llm_extraction and event_in.raw_text:
        try:
            extracted = await state.llm.extract_memory_objects(event_in.raw_text, event_in.event_type)
            event.payload["llm_extracted"] = extracted
        except Exception:
            pass
    report = state.writer.capture_event(event)
    return report


@router.post("/memory/read", response_model=List[MemoryObject])
async def memory_read(req: MemoryReadIn):
    request = MemoryRequest(
        project_id=req.project_id,
        session_id=req.session_id,
        query=req.query,
        task_type=req.task_type,
        token_budget=req.token_budget,
        retrieval_requirements=req.retrieval_requirements,
    )
    plan = state.router.make_plan(request)
    candidates = state.reader.retrieve(request, plan)
    scored = state.scorer.rerank(candidates, request)
    return [m for m, _ in scored[:50]]


@router.get("/memory/{memory_id}")
async def memory_get(memory_id: str):
    mem = state.store.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


@router.get("/memory/{memory_id}/graph")
async def memory_graph(memory_id: str, max_hops: int = 2):
    expanded = state.graph_expander.expand([memory_id], max_hops=max_hops)
    return {"seed": memory_id, "expanded": expanded}


@router.post("/memory/graph/expand")
async def graph_expand(body: GraphExpandIn):
    expanded = state.graph_expander.expand(body.memory_ids, max_hops=body.max_hops)
    return {"seeds": body.memory_ids, "expanded": expanded}


@router.post("/memory/reflect")
async def memory_reflect(body: ReflectIn):
    mem = await state.reflection.maybe_reflect(body.project_id, body.trigger, body.min_evidence)
    if mem:
        return {"status": "created", "memory": mem}
    return {"status": "insufficient_evidence"}


@router.post("/memory/decay")
async def memory_decay(body: DecayIn):
    stats = state.decay.run_decay(body.project_id)
    return {"status": "ok", "stats": stats}


@router.post("/memory/stale")
async def memory_stale(body: StaleCheckIn):
    result = state.stale_checker.flag_stale_memories(body.project_id, body.workspace_root)
    return {"status": "ok", "stale": result}


@router.post("/memory/correct")
async def memory_correct(body: CorrectionIn):
    from vcm_os.memory.correction import CorrectionService, MemoryCorrection
    service = CorrectionService(state.store)
    corr = MemoryCorrection(
        memory_id=body.memory_id,
        action=body.action,
        reason=body.reason,
        user_id=body.user_id,
    )
    result = service.apply(corr)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Correction failed"))
    return result


@router.get("/memory/{memory_id}/corrections")
async def memory_corrections(memory_id: str):
    from vcm_os.memory.correction import CorrectionService
    service = CorrectionService(state.store)
    return {"history": service.get_correction_history(memory_id)}


@router.get("/memory/review-queue/{project_id}")
async def memory_review_queue(project_id: str, limit: int = 20):
    from vcm_os.memory.correction import CorrectionService
    service = CorrectionService(state.store)
    queue = service.get_review_queue(project_id, limit=limit)
    return {"queue": queue}


@router.get("/memory/correction-stats/{project_id}")
async def memory_correction_stats(project_id: str):
    from vcm_os.memory.correction import CorrectionService
    service = CorrectionService(state.store)
    return service.get_correction_stats(project_id)
