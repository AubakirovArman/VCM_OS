from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from vcm_os.schemas.common import generate_id, utc_now
from vcm_os.schemas.enums import SessionStatus


class SessionIdentity(BaseModel):
    session_id: str = Field(default_factory=lambda: generate_id("sess"))
    project_id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    last_active_at: datetime = Field(default_factory=utc_now)
    status: SessionStatus = SessionStatus.ACTIVE
    branch: Optional[str] = None
    workspace_root: Optional[str] = None
    active_goal_ids: List[str] = Field(default_factory=list)


class SessionState(BaseModel):
    session_id: str
    active_goals: List[str] = Field(default_factory=list)
    active_files: List[str] = Field(default_factory=list)
    current_plan: Optional[str] = None
    open_tasks: List[str] = Field(default_factory=list)
    recent_decisions: List[str] = Field(default_factory=list)
    recent_errors: List[str] = Field(default_factory=list)
    current_code_branch: Optional[str] = None
    tool_state: Optional[Dict[str, Any]] = None
    unresolved_assumptions: List[str] = Field(default_factory=list)
    last_checkpoint_id: Optional[str] = None


class SessionCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: generate_id("chk"))
    session_id: str
    project_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    state: SessionState
    packed_summary: Optional[str] = None
