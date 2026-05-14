from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from vcm_os.schemas.common import generate_id, utc_now
from vcm_os.schemas.enums import (
    EvidenceStrength,
    MemoryType,
    SourceType,
    Stability,
    Validity,
)


class SourcePointer(BaseModel):
    event_id: Optional[str] = None
    file_path: Optional[str] = None
    line_range: Optional[List[int]] = None
    commit_hash: Optional[str] = None
    chat_turn: Optional[int] = None


class DecisionEntry(BaseModel):
    decision_id: str = Field(default_factory=lambda: generate_id("dec"))
    statement: str
    rationale: Optional[str] = None
    status: Validity = Validity.ACTIVE
    alternatives: Optional[List[str]] = None
    rejected_alternatives: Optional[List[str]] = None
    tradeoffs: Optional[str] = None
    confidence: float = 0.5
    owner: Optional[str] = None
    affected_files: List[str] = Field(default_factory=list)
    affected_tasks: List[str] = Field(default_factory=list)


class ErrorEntry(BaseModel):
    error_id: str = Field(default_factory=lambda: generate_id("err"))
    kind: str
    message: str
    root_cause: Optional[str] = None
    fix_attempt: Optional[str] = None
    verified_fix: Optional[str] = None
    commands_run: List[str] = Field(default_factory=list)
    test_results: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    recurrence_risk: float = 0.0


class EntityRef(BaseModel):
    type: str
    name: str


class MemoryObject(BaseModel):
    memory_id: str = Field(default_factory=lambda: generate_id("mem"))
    project_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "user_local_001"
    timestamp: datetime = Field(default_factory=utc_now)

    memory_type: MemoryType
    source_type: SourceType
    source_pointer: Optional[SourcePointer] = None

    raw_text: Optional[str] = None
    compressed_summary: Optional[str] = None
    semantic_summary: Optional[str] = None

    entities: List[EntityRef] = Field(default_factory=list)
    intents: List[str] = Field(default_factory=list)
    decisions: List[DecisionEntry] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    code_references: List[Dict[str, Any]] = Field(default_factory=list)
    file_references: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    errors_found: List[ErrorEntry] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)

    importance_score: float = 0.5
    recency_score: float = 1.0
    confidence_score: float = 0.5
    stability: Stability = Stability.VOLATILE
    validity: Validity = Validity.ACTIVE
    evidence_strength: EvidenceStrength = EvidenceStrength.INFERRED

    contradiction_links: List[str] = Field(default_factory=list)
    dependency_links: List[str] = Field(default_factory=list)
    parent_memory_id: Optional[str] = None
    child_memory_ids: List[str] = Field(default_factory=list)
    graph_node_ids: List[str] = Field(default_factory=list)

    embedding_vector: Optional[List[float]] = None
    embedding_model: Optional[str] = None

    access_scope: str = "private_project"
    cross_session: bool = False
    cross_project: bool = False

    ttl_days: Optional[int] = None
    decay_policy: str = "typed_decay_v1"
    never_delete: bool = False

    version: int = 1
    schema_version: str = "memory_object_v0.3"
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("audit_log", mode="before")
    @classmethod
    def init_audit(cls, v):
        if not v:
            return [{"timestamp": utc_now().isoformat(), "actor": "system", "action": "created"}]
        return v
