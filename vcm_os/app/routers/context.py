from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import ContextBuildIn
from vcm_os.schemas import MemoryRequest

router = APIRouter()


@router.post("/context/build")
async def context_build(req: ContextBuildIn):
    request = MemoryRequest(
        project_id=req.project_id,
        session_id=req.session_id,
        query=req.query,
        task_type=req.task_type,
        token_budget=req.token_budget,
        max_pack_tokens=req.max_pack_tokens,
    )
    plan = state.router.make_plan(request)
    candidates = state.reader.retrieve(request, plan)
    scored = state.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]

    checkpoint = None
    active_state = None
    session = None
    if req.session_id:
        checkpoint = state.checkpoint_manager.load_latest_checkpoint(req.session_id)
        active_state = state.session_store.get_session_state(req.session_id)
        session = state.session_store.get_session(req.session_id)

    pack = state.pack_builder.build(request, memories, checkpoint, active_state, session)

    if req.check_sufficiency:
        suff = await state.sufficiency.check(req.query, pack)
        pack.sufficiency_score = suff.get("score", pack.sufficiency_score)
        if not suff.get("sufficient", True):
            pack.warnings.append(f"Pack may be insufficient. Missing: {suff.get('missing', [])}")

    return pack


@router.post("/context/prompt")
async def context_prompt(req: ContextBuildIn):
    pack = await context_build(req)
    prompt = state.prompt_composer.compose(pack, req.query)
    return {"prompt": prompt, "pack": pack}
