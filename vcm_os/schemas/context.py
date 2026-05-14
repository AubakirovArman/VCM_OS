from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from vcm_os.schemas.common import generate_id, utc_now


class MemoryRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: generate_id("req"))
    user_id: str = "user_local_001"
    project_id: str
    session_id: Optional[str] = None
    query: str
    task_type: str = "general"
    token_budget: int = 32768
    max_pack_tokens: int = 65
    retrieval_requirements: Dict[str, Any] = Field(default_factory=dict)
    privacy_scope: str = "current_project_only"
    required_terms: List[str] = Field(default_factory=list)


class ContextPackSection(BaseModel):
    section_name: str
    content: str
    memory_ids: List[str] = Field(default_factory=list)
    token_estimate: int = 0


class ContextPack(BaseModel):
    pack_id: str = Field(default_factory=lambda: generate_id("pack"))
    project_id: str
    session_id: Optional[str] = None
    sections: List[ContextPackSection] = Field(default_factory=list)
    token_estimate: int = 0
    sufficiency_score: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    forbidden_context: List[str] = Field(default_factory=list)
    trace_log: Optional[Dict] = None  # v0.7 pipeline trace


class RetrievalPlan(BaseModel):
    needs_session: bool = True
    needs_project: bool = True
    needs_decisions: bool = True
    needs_errors: bool = True
    needs_code: bool = True
    needs_graph: bool = False
    max_graph_hops: int = 2


class WriteReport(BaseModel):
    objects_written: int = 0
    objects_linked: int = 0
    contradictions_found: int = 0
    ledgers_updated: int = 0
    errors: List[str] = Field(default_factory=list)
