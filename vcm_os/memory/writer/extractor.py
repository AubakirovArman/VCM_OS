from typing import Dict, List, Optional

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


class ExtractorMixin:
    def extract_from_event(self, event: EventRecord) -> List[MemoryObject]:
        objects: List[MemoryObject] = []
        text = event.raw_text or ""
        payload = event.payload or {}

        objects.append(
            MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.EVENT,
                source_type=SourceType.TOOL_OUTPUT if event.event_type == "tool_call" else SourceType.USER_MESSAGE,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=text[:500] if text else None,
                semantic_summary=text[:500] if text else None,
            )
        )

        llm_extracted = payload.get("llm_extracted")
        if isinstance(llm_extracted, list):
            for item in llm_extracted:
                try:
                    obj = self._from_llm_extracted(event, item)
                    if obj:
                        objects.append(obj)
                except Exception:
                    pass
            return objects

        llm_items = self.llm_extractor.extract(event.event_type, text)
        if llm_items:
            seen_texts = set()
            for item in llm_items:
                try:
                    obj = self._from_llm_extracted(event, item)
                    if obj:
                        key = (obj.memory_type.value, obj.compressed_summary or "")[:100]
                        if key in seen_texts:
                            continue
                        seen_texts.add(key)
                        objects.append(obj)
                except Exception:
                    pass
            if len(objects) > 1:
                return objects

        if event.event_type == "user_message":
            objects.extend(self._extract_user_message(event, text, payload))
        elif event.event_type == "assistant_response":
            objects.extend(self._extract_assistant_response(event, text, payload))
        elif event.event_type == "tool_call":
            objects.extend(self._extract_tool_output(event, text, payload))
        elif event.event_type == "code_change":
            objects.extend(self._extract_code_change(event, text, payload))
        elif event.event_type == "error":
            objects.extend(self._extract_error(event, text, payload))

        return objects

    def _from_llm_extracted(self, event: EventRecord, item: Dict) -> Optional[MemoryObject]:
        mem_type = item.get("memory_type", "fact")
        try:
            mt = MemoryType(mem_type)
        except ValueError:
            mt = MemoryType.FACT

        entities = []
        for e in item.get("entities", []):
            if isinstance(e, dict) and "type" in e and "name" in e:
                entities.append(EntityRef(type=e["type"], name=e["name"]))

        decisions = []
        if mt == MemoryType.DECISION or item.get("rationale") or item.get("alternatives"):
            status_str = item.get("status", "active")
            try:
                status = Validity(status_str)
            except ValueError:
                status = Validity.ACTIVE
            decisions.append(DecisionEntry(
                statement=item.get("summary", ""),
                rationale=item.get("rationale"),
                status=status,
                alternatives=item.get("alternatives"),
            ))

        errors_found = []
        if mt == MemoryType.ERROR or item.get("error_kind") or item.get("error_message"):
            errors_found.append(ErrorEntry(
                kind=item.get("error_kind", "runtime_error"),
                message=item.get("error_message", item.get("summary", "")),
                root_cause=item.get("root_cause"),
                fix_attempt=item.get("fix_attempt"),
                verified_fix=item.get("verified_fix"),
            ))

        if event.event_type == "user_message":
            src = SourceType.USER_MESSAGE
        elif event.event_type == "assistant_response":
            src = SourceType.ASSISTANT_MESSAGE
        elif event.event_type == "tool_call":
            src = SourceType.TOOL_OUTPUT
        elif event.event_type == "code_change":
            src = SourceType.CODE_DIFF
        else:
            src = SourceType.USER_MESSAGE

        return MemoryObject(
            project_id=event.project_id,
            session_id=event.session_id,
            memory_type=mt,
            source_type=src,
            source_pointer=SourcePointer(event_id=event.event_id),
            raw_text=event.raw_text,
            compressed_summary=item.get("summary", "")[:500],
            semantic_summary=item.get("summary", "")[:500],
            entities=entities,
            file_references=item.get("file_references", []),
            decisions=decisions,
            errors_found=errors_found,
            importance_score=item.get("importance", 0.5),
            confidence_score=item.get("confidence", 0.5),
            validity=Validity.ACTIVE,
        )
