from fastapi import APIRouter, HTTPException

import vcm_os.app.state as state
from vcm_os.app.models import SummaryIn

router = APIRouter()


@router.post("/summaries/session")
async def summary_session(body: SummaryIn):
    if not body.session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    text = await state.summary_gen.generate_session_summary(body.session_id)
    return {"session_id": body.session_id, "summary": text}


@router.post("/summaries/project")
async def summary_project(body: SummaryIn):
    if not body.project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    text = await state.summary_gen.generate_project_summary(body.project_id)
    return {"project_id": body.project_id, "summary": text}


@router.post("/summaries/file")
async def summary_file(body: SummaryIn):
    if not body.file_path or not body.file_content:
        raise HTTPException(status_code=400, detail="file_path and file_content required")
    text = await state.summary_gen.generate_file_summary(body.file_path, body.file_content)
    return {"file_path": body.file_path, "summary": text}
