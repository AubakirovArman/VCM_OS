# Re-export all schema types for backward compatibility.

from vcm_os.schemas.common import generate_id, utc_now
from vcm_os.schemas.context import (
    ContextPack,
    ContextPackSection,
    MemoryRequest,
    RetrievalPlan,
    WriteReport,
)
from vcm_os.schemas.enums import (
    EvidenceStrength,
    MemoryType,
    SessionStatus,
    SourceType,
    Stability,
    TaskType,
    Validity,
)
from vcm_os.schemas.event import EventRecord
from vcm_os.schemas.memory import (
    DecisionEntry,
    EntityRef,
    ErrorEntry,
    MemoryObject,
    SourcePointer,
)
from vcm_os.schemas.session import (
    SessionCheckpoint,
    SessionIdentity,
    SessionState,
)

__all__ = [
    "generate_id",
    "utc_now",
    "ContextPack",
    "ContextPackSection",
    "MemoryRequest",
    "RetrievalPlan",
    "WriteReport",
    "EvidenceStrength",
    "MemoryType",
    "SessionStatus",
    "SourceType",
    "Stability",
    "TaskType",
    "Validity",
    "EventRecord",
    "DecisionEntry",
    "EntityRef",
    "ErrorEntry",
    "MemoryObject",
    "SourcePointer",
    "SessionCheckpoint",
    "SessionIdentity",
    "SessionState",
]
