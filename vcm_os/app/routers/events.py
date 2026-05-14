from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import EventIn
from vcm_os.schemas import EventRecord, WriteReport

router = APIRouter()


@router.post("/events", response_model=WriteReport)
async def post_event(event_in: EventIn):
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
