from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

import vcm_os.app.state as state
from vcm_os.app.models import CheckpointIn, SessionCreateIn
from vcm_os.schemas import SessionIdentity, SessionState

router = APIRouter()


@router.post("/session/create", response_model=SessionIdentity)
async def session_create(body: SessionCreateIn):
    return state.session_store.create_session(body.project_id, body.title, body.branch)


@router.get("/session/{session_id}")
async def session_get(session_id: str):
    sess = state.session_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


@router.post("/session/{session_id}/state")
async def session_update_state(session_id: str, state_data: Dict[str, Any]):
    existing = state.session_store.get_session_state(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    for key, value in state_data.items():
        if hasattr(existing, key):
            setattr(existing, key, value)
    state.session_store.update_session_state(existing)
    return existing


@router.post("/session/{session_id}/pause")
async def session_pause(session_id: str):
    state.session_store.pause_session(session_id)
    return {"status": "paused"}


@router.post("/session/{session_id}/activate")
async def session_activate(session_id: str):
    state.session_store.activate_session(session_id)
    return {"status": "active"}


@router.post("/session/{session_id}/restore")
async def session_restore(session_id: str, query: Optional[str] = "resume work"):
    return state.restorer.restore(session_id, query or "resume work")


@router.post("/session/save")
async def session_save(cp_in: CheckpointIn):
    st = SessionState(**cp_in.state)
    cp = state.checkpoint_manager.save_checkpoint(cp_in.session_id, cp_in.project_id, st, cp_in.packed_summary)
    return cp
