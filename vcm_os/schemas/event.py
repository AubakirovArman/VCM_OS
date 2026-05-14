from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from vcm_os.schemas.common import generate_id, utc_now


class EventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: generate_id("evt"))
    session_id: Optional[str] = None
    project_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    raw_text: Optional[str] = None
