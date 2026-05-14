from typing import Optional

from fastapi import APIRouter, HTTPException

import vcm_os.app.state as state
from vcm_os.app.models import DecisionActionIn, ErrorFixIn

router = APIRouter()


@router.get("/project/{project_id}/decisions")
async def project_decisions(project_id: str, session_id: Optional[str] = None):
    return state.decision_ledger.get_active_decisions(project_id, session_id)


@router.post("/project/decisions/action")
async def decision_action(body: DecisionActionIn):
    if body.action == "confirm":
        state.decision_ledger.confirm_decision(body.decision_id)
    elif body.action == "reject":
        state.decision_ledger.reject_decision(body.decision_id)
    elif body.action == "supersede":
        if not body.new_decision_id:
            raise HTTPException(status_code=400, detail="new_decision_id required for supersede")
        state.decision_ledger.supersede_decision(body.decision_id, body.new_decision_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    return {"status": "ok"}


@router.get("/project/{project_id}/errors")
async def project_errors(project_id: str, session_id: Optional[str] = None, kind: Optional[str] = None):
    return state.error_ledger.get_errors(project_id, session_id, kind)


@router.post("/project/errors/fix")
async def error_fix(body: ErrorFixIn):
    state.error_ledger.add_verified_fix(body.error_memory_id, body.fix_text)
    return {"status": "ok"}


@router.get("/project/{project_id}/state")
async def project_state(project_id: str):
    """Return consolidated project state: decisions, errors, goals."""
    decisions = state.decision_ledger.get_active_decisions(project_id)
    errors = state.error_ledger.get_errors(project_id)
    goals = state.store.get_memories(project_id=project_id, memory_type="goal", limit=20)
    return {
        "project_id": project_id,
        "total_memories": len(state.store.get_memories(project_id=project_id, limit=10000)),
        "active_decisions": [
            {"id": d.memory_id, "text": (d.raw_text or d.compressed_summary or "")[:200]}
            for d in decisions
        ],
        "recent_errors": [
            {"id": e.memory_id, "text": (e.raw_text or e.compressed_summary or "")[:200]}
            for e in errors[:10]
        ],
        "active_goals": [
            {"id": g.memory_id, "text": (g.raw_text or g.compressed_summary or "")[:200]}
            for g in goals
        ],
    }
