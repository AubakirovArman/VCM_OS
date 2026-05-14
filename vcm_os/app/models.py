from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EventIn(BaseModel):
    session_id: Optional[str] = None
    project_id: str
    event_type: str
    payload: Dict[str, Any] = {}
    raw_text: Optional[str] = None
    use_llm_extraction: bool = False


class MemoryReadIn(BaseModel):
    project_id: str
    session_id: Optional[str] = None
    query: str
    task_type: str = "general"
    token_budget: int = 32768
    retrieval_requirements: Dict[str, Any] = {}


class ContextBuildIn(BaseModel):
    project_id: str
    session_id: Optional[str] = None
    query: str
    task_type: str = "general"
    token_budget: int = 32768
    max_pack_tokens: int = 65
    check_sufficiency: bool = False


class SessionCreateIn(BaseModel):
    project_id: str
    title: Optional[str] = None
    branch: Optional[str] = None


class CheckpointIn(BaseModel):
    session_id: str
    project_id: str
    state: Dict[str, Any]
    packed_summary: Optional[str] = None


class DecisionActionIn(BaseModel):
    decision_id: str
    action: str
    new_decision_id: Optional[str] = None


class ErrorFixIn(BaseModel):
    error_memory_id: str
    fix_text: str


class ReflectIn(BaseModel):
    project_id: str
    trigger: str = "session_end"
    min_evidence: int = 3


class DecayIn(BaseModel):
    project_id: str


class StaleCheckIn(BaseModel):
    project_id: str
    workspace_root: Optional[str] = None


class GraphExpandIn(BaseModel):
    memory_ids: List[str]
    max_hops: int = 2


class QueryRewriteIn(BaseModel):
    query: str
    task_type: str = "general"


class CodebaseIndexIn(BaseModel):
    project_id: str
    directory: str


class VerifyIn(BaseModel):
    query: str
    answer: str
    project_id: str
    session_id: Optional[str] = None
    use_llm: bool = False


class SummaryIn(BaseModel):
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    file_path: Optional[str] = None
    file_content: Optional[str] = None


class SymbolQueryIn(BaseModel):
    name: str


class AffectedSymbolsIn(BaseModel):
    file_path: str
    changed_lines: List[int]


class RetentionIn(BaseModel):
    max_age_days: int = 90
    max_memories_per_project: int = 1000


class CorrectionIn(BaseModel):
    memory_id: str
    action: str  # stale, incorrect, important, duplicate, pin, unpin, delete
    reason: str = ""
    user_id: str = ""
