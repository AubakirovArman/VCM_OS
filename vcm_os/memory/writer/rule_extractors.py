import re
from typing import Dict, List

from vcm_os.memory.writer.session_extractors import SessionErrorExtractor, SessionGoalExtractor
from vcm_os.schemas import (
    DecisionEntry,
    EntityRef,
    ErrorEntry,
    EventRecord,
    MemoryObject,
    MemoryType,
    SourcePointer,
    SourceType,
    Validity,
)


def _extract_rationale(text: str) -> str:
    m = re.search(r"(?:Rationale|Because|Reason|rationale|because|reason)[\s:—]+([^\n.]{10,200})", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_alternatives(text: str) -> List[str]:
    alts = []
    for m in re.finditer(r"(?:Alternative|Instead of|Option|alternative|instead of|option)[\s:—]+([^\n.]{5,120})", text, re.IGNORECASE):
        alts.append(m.group(1).strip())
    return alts[:3]


def _extract_file_refs(text: str) -> List[str]:
    refs = []
    for m in re.finditer(r"([a-zA-Z0-9_\-/]+\.(?:py|ts|js|rs|go|java|c|cpp|h|yaml|yml|json|toml|md|txt))", text):
        refs.append(m.group(1))
    return list(dict.fromkeys(refs))[:5]


def _extract_tradeoffs(text: str) -> str:
    m = re.search(r"(?:Tradeoff|Pros? and cons?|Trade-off|tradeoff|pros? and cons?)[\s:—]+([^\n]{10,300})", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_root_cause(text: str) -> str:
    m = re.search(r"(?:Root cause|Rootcause|Caused by|Cause)[\s:—]+(.{5,300}?)(?=\n|\.\s+(?:Fix|Verified|Alternative|Tradeoff)|\Z)", text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_fix_attempt(text: str) -> str:
    m = re.search(r"(?:Fix attempt|Fix|Attempted fix|Attempt)[\s:—]+(.{5,300}?)(?=\n|\.\s+(?:Verified|Root cause|Alternative|Tradeoff)|\Z)", text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_verified_fix(text: str) -> str:
    m = re.search(r"(?:Verified fix|Verified|Confirmed fix|Confirmed)[\s:—]+(.{5,300}?)(?=\n|\.\s+(?:Recurrence|Root cause|Fix|Alternative)|\Z)", text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_recurrence_risk(text: str) -> int:
    text_lower = text.lower()
    if "high risk" in text_lower or "high recurrence" in text_lower:
        return 3
    if "medium risk" in text_lower or "medium recurrence" in text_lower:
        return 2
    if "low risk" in text_lower or "low recurrence" in text_lower:
        return 1
    if "recurrence risk" in text_lower:
        return 2  # default if mentioned but not qualified
    return 0


class RuleExtractorMixin:
    def _extract_user_message(self, event: EventRecord, text: str, payload: Dict) -> List[MemoryObject]:
        objs = []
        objs.append(
            MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.INTENT,
                source_type=SourceType.USER_MESSAGE,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"User intent: {text[:300]}",
                semantic_summary=text[:400],
                intents=[text[:200]],
            )
        )
        text_lower = text.lower()
        has_decision = (
            text_lower.startswith("decision:")
            or text_lower.startswith("use ")
            or ": decision" in text_lower
            or ": use " in text_lower
            or " decide to " in text_lower
            or " will use " in text_lower
            or " going with " in text_lower
            or " choose " in text_lower
            or " decided to " in text_lower
        )
        if has_decision:
            stmt = text
            if stmt.lower().startswith("decision:"):
                stmt = stmt[9:].strip()
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.DECISION,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Decision: {stmt[:300]}",
                    decisions=[DecisionEntry(
                        statement=stmt[:400],
                        status=Validity.ACTIVE,
                        rationale=_extract_rationale(text),
                        alternatives=_extract_alternatives(text),
                        tradeoffs=_extract_tradeoffs(text),
                    )],
                    validity=Validity.ACTIVE,
                )
            )
        # Enhanced error extraction from session logs
        error_ext = SessionErrorExtractor()
        errors = error_ext.extract(text)
        if errors:
            for err in errors:
                # Parse v2 fields from error text
                root_cause = _extract_root_cause(text)
                fix_attempt = _extract_fix_attempt(text)
                verified_fix = _extract_verified_fix(text)
                recurrence_risk = _extract_recurrence_risk(text)
                objs.append(
                    MemoryObject(
                        project_id=event.project_id,
                        session_id=event.session_id,
                        memory_type=MemoryType.ERROR,
                        source_type=SourceType.USER_MESSAGE,
                        source_pointer=SourcePointer(event_id=event.event_id),
                        raw_text=text,
                        compressed_summary=f"Error: {err[:300]}",
                        errors_found=[ErrorEntry(
                            kind="session_error",
                            message=err[:400],
                            affected_files=_extract_file_refs(text),
                            root_cause=root_cause,
                            fix_attempt=fix_attempt,
                            verified_fix=verified_fix,
                            recurrence_risk=recurrence_risk,
                        )],
                    )
                )
        elif any(k in text.lower() for k in ("error:", "error ", "bug:", "bug ", "failed", "failure", "exception", "crash", "injection", "leak", "degraded")):
            msg = text
            if msg.lower().startswith("error:"):
                msg = msg[6:].strip()
            root_cause = _extract_root_cause(text)
            fix_attempt = _extract_fix_attempt(text)
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.ERROR,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Error: {msg[:300]}",
                    errors_found=[ErrorEntry(
                        kind="runtime_error",
                        message=msg[:400],
                        affected_files=_extract_file_refs(text),
                        root_cause=root_cause,
                        fix_attempt=fix_attempt,
                    )],
                )
            )

        # Session goal extraction
        goal_ext = SessionGoalExtractor()
        goals = goal_ext.extract(text)
        for goal in goals:
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.GOAL,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Goal: {goal[:300]}",
                )
            )
        if any(k in text.lower() for k in ("must ", "should ", "need to", "requirement", "constraint")):
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.REQUIREMENT,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Requirement: {text[:300]}",
                    constraints=[text[:300]],
                )
            )
        # Goal extraction (v0.9): detect explicit goal phrases
        goal_lower = text.lower()
        has_goal = (
            goal_lower.startswith("goal:")
            or goal_lower.startswith("our goal")
            or goal_lower.startswith("the goal")
            or goal_lower.startswith("objective:")
            or goal_lower.startswith("aim:")
            or " our goal is " in goal_lower
            or " the goal is " in goal_lower
            or " objective is " in goal_lower
            or " need to " in goal_lower
            or " we need to " in goal_lower
            or " we must " in goal_lower
            or " target is " in goal_lower
        )
        if has_goal:
            stmt = text
            for prefix in ["Goal:", "Our goal", "The goal", "Objective:", "Aim:"]:
                if stmt.lower().startswith(prefix.lower()):
                    stmt = stmt[len(prefix):].strip()
                    break
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.GOAL,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Goal: {stmt[:60]}",
                    intents=[stmt[:200]],
                )
            )
        has_task = (
            text_lower.startswith("task:")
            or ": task" in text_lower
            or " todo " in text_lower
            or " implement " in text_lower
            or " create " in text_lower
            or " add " in text_lower
        )
        if has_task:
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.TASK,
                    source_type=SourceType.USER_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Task: {text[:300]}",
                    open_questions=[text[:300]],
                )
            )
        file_refs = re.findall(r"[\w\-/]+\.(py|ts|js|tsx|jsx|rs|go|java|cpp|c|h|yaml|yml|json|toml|md)", text)
        if file_refs:
            for obj in objs:
                obj.file_references = list(set(file_refs))
        return objs

    def _extract_assistant_response(self, event: EventRecord, text: str, payload: Dict) -> List[MemoryObject]:
        objs = []
        objs.append(
            MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.TASK,
                source_type=SourceType.ASSISTANT_MESSAGE,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Assistant plan: {text[:300]}",
                semantic_summary=text[:400],
                validity=Validity.PROPOSED,
            )
        )
        if any(k in text.lower() for k in ("propose", "suggest", "recommend", "should use", "decision:")):
            stmt = text
            if stmt.lower().startswith("decision:"):
                stmt = stmt[9:].strip()
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.DECISION,
                    source_type=SourceType.ASSISTANT_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Proposed decision: {stmt[:300]}",
                    decisions=[DecisionEntry(
                        statement=stmt[:400],
                        status=Validity.PROPOSED,
                        rationale=_extract_rationale(text),
                        alternatives=_extract_alternatives(text),
                        tradeoffs=_extract_tradeoffs(text),
                    )],
                    validity=Validity.PROPOSED,
                )
            )
        # Error v2 extraction from assistant responses (fix attempts, verified fixes)
        if any(k in text.lower() for k in ("fix attempt", "verified fix", "root cause", "recurrence risk", "error:", "bug:")):
            root_cause = _extract_root_cause(text)
            fix_attempt = _extract_fix_attempt(text)
            verified_fix = _extract_verified_fix(text)
            recurrence_risk = _extract_recurrence_risk(text)
            if root_cause or fix_attempt or verified_fix or recurrence_risk > 0:
                objs.append(
                    MemoryObject(
                        project_id=event.project_id,
                        session_id=event.session_id,
                        memory_type=MemoryType.ERROR,
                        source_type=SourceType.ASSISTANT_MESSAGE,
                        source_pointer=SourcePointer(event_id=event.event_id),
                        raw_text=text,
                        compressed_summary=f"Error fix: {text[:300]}",
                        errors_found=[ErrorEntry(
                            kind="session_error",
                            message=text[:400],
                            affected_files=_extract_file_refs(text),
                            root_cause=root_cause,
                            fix_attempt=fix_attempt,
                            verified_fix=verified_fix,
                            recurrence_risk=recurrence_risk,
                        )],
                    )
                )

        questions = re.findall(r"\?[^.!?]*", text)
        if questions:
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.UNCERTAINTY,
                    source_type=SourceType.ASSISTANT_MESSAGE,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    open_questions=questions[:5],
                )
            )
        return objs

    def _extract_tool_output(self, event: EventRecord, text: str, payload: Dict) -> List[MemoryObject]:
        from vcm_os.memory.writer.tool_ingestor import ToolResultIngestor
        ingestor = ToolResultIngestor()
        objs = ingestor.ingest(event)
        tool_name = payload.get("tool_name", "unknown")
        if any(k in tool_name.lower() for k in ("test", "pytest", "jest", "mocha")):
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.FACT,
                    source_type=SourceType.TEST_RESULT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Test result ({tool_name}): {text[:300]}",
                    tools_used=[tool_name],
                )
            )
        if "error" in text.lower() or "fail" in text.lower() or "traceback" in text.lower():
            objs.append(
                MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.ERROR,
                    source_type=SourceType.TOOL_OUTPUT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Error: {text[:300]}",
                    errors_found=[ErrorEntry(kind="tool_error", message=text[:500])],
                )
            )
        return objs

    def _extract_code_change(self, event: EventRecord, text: str, payload: Dict) -> List[MemoryObject]:
        file_path = payload.get("file_path", "unknown")
        # Use actual change text for better pack coverage instead of generic "Code change in..."
        summary = text[:120] if len(text) > 120 else text
        objs = [
            MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.CODE_CHANGE,
                source_type=SourceType.CODE_DIFF,
                source_pointer=SourcePointer(event_id=event.event_id, file_path=file_path),
                raw_text=text,
                compressed_summary=summary,
                file_references=[file_path],
                entities=[EntityRef(type="file", name=file_path)],
            )
        ]
        return objs

    def _extract_error(self, event: EventRecord, text: str, payload: Dict) -> List[MemoryObject]:
        kind = payload.get("error_kind", "runtime_error")
        return [
            MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.RUNTIME_ERROR,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Error ({kind}): {text[:300]}",
                errors_found=[ErrorEntry(kind=kind, message=text[:500])],
            )
        ]
