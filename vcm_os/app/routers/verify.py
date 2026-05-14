from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import VerifyIn
from vcm_os.schemas import MemoryRequest

router = APIRouter()


@router.post("/verify")
async def verify_answer(body: VerifyIn):
    request = MemoryRequest(
        project_id=body.project_id,
        session_id=body.session_id,
        query=body.query,
    )
    plan = state.router.make_plan(request)
    candidates = state.reader.retrieve(request, plan)
    scored = state.scorer.rerank(candidates, request)
    memories = [m for m, _ in scored[:50]]

    checkpoint = None
    active_state = None
    session = None
    if body.session_id:
        checkpoint = state.checkpoint_manager.load_latest_checkpoint(body.session_id)
        active_state = state.session_store.get_session_state(body.session_id)
        session = state.session_store.get_session(body.session_id)

    pack = state.pack_builder.build(request, memories, checkpoint, active_state, session)

    if body.use_llm:
        result = await state.verifier.verify_with_llm(body.query, body.answer, pack)
    else:
        result = state.verifier.verify_answer(body.query, body.answer, pack)
    return result
