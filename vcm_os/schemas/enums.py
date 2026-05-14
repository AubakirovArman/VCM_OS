from enum import Enum


class MemoryType(str, Enum):
    DECISION = "decision"
    ERROR = "error"
    REQUIREMENT = "requirement"
    FACT = "fact"
    INTENT = "intent"
    CODE_CHANGE = "code_change"
    PROCEDURE = "procedure"
    REFLECTION = "reflection"
    UNCERTAINTY = "uncertainty"
    PREFERENCE = "preference"
    TASK = "task"
    CHECKPOINT = "checkpoint"
    EVENT = "event"
    GOAL = "goal"


class SourceType(str, Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_OUTPUT = "tool_output"
    CODE_DIFF = "code_diff"
    TEST_RESULT = "test_result"
    RUNTIME_ERROR = "runtime_error"
    FILE_SNAPSHOT = "file_snapshot"
    MANUAL_NOTE = "manual_note"


class Validity(str, Enum):
    ACTIVE = "active"
    PROPOSED = "proposed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DISPUTED = "disputed"


class Stability(str, Enum):
    VOLATILE = "volatile"
    STABLE = "stable"
    CANONICAL = "canonical"


class EvidenceStrength(str, Enum):
    DIRECT_USER_STATEMENT = "direct_user_statement"
    TOOL_VERIFIED = "tool_verified"
    INFERRED = "inferred"
    WEAK = "weak"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TaskType(str, Enum):
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    FEATURE = "feature"
    RESEARCH = "research"
    GENERAL = "general"
