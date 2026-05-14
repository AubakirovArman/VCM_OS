import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

from vcm_os.schemas import (
    EventRecord,
    MemoryObject,
    MemoryType,
    WriteReport,
)
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.memory.llm_extractor import LLMExtractor
from vcm_os.memory.linker import AutoLinker
from vcm_os.memory.redactor import SecretRedactor


class MemoryWriterCore:
    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
    ):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.llm_extractor = LLMExtractor()
        self.redactor = SecretRedactor()
        self.auto_linker = AutoLinker(store)

    def capture_event(self, event: EventRecord) -> WriteReport:
        self.store.insert_event(event)
        objects = self.extract_from_event(event)

        deduped = []
        seen_keys = set()
        for obj in objects:
            key = (obj.memory_type.value, obj.raw_text or "", obj.session_id or "")
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(obj)
        objects = deduped

        for obj in objects:
            # Redact secrets before scoring and storing
            obj.raw_text = self.redactor.redact(obj.raw_text)
            obj.compressed_summary = self.redactor.redact(obj.compressed_summary)
            obj.semantic_summary = self.redactor.redact(obj.semantic_summary)
            obj.importance_score = self._score_importance(obj)
            obj.confidence_score = self._score_confidence(obj)
            obj.recency_score = 1.0

        linked_count = 0
        contradictions = 0
        for obj in objects:
            # Use enhanced auto-linker for comprehensive linking
            linked = self.auto_linker.link(obj)
            linked_count += len(linked)
            contradictions += self._detect_contradictions(obj)

        skipped_duplicates = 0
        self._last_skip_count = 0
        existing = self.store.get_memories(project_id=event.project_id, limit=200)
        existing_hashes = {}
        for ex in existing:
            norm = " ".join((ex.raw_text or "").strip().lower().split())
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            key = (ex.project_id, ex.session_id or "", ex.memory_type.value, h)
            existing_hashes[key] = ex.memory_id

        texts = []
        for obj in objects:
            norm = " ".join((obj.raw_text or "").strip().lower().split())
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            key = (obj.project_id, obj.session_id or "", obj.memory_type.value, h)
            if key in existing_hashes:
                skipped_duplicates += 1
                self._last_skip_count += 1
                continue
            self.store.insert_memory(obj)
            existing_hashes[key] = obj.memory_id
            text = obj.semantic_summary or obj.compressed_summary or obj.raw_text or ""
            texts.append((obj.memory_id, text))
            if obj.memory_type == MemoryType.DECISION:
                self._update_decision_ledger(obj)
            if obj.memory_type == MemoryType.ERROR:
                self._update_error_ledger(obj)

        if texts:
            self.vector_index.add_batch(texts)
            self.sparse_index.add_batch(texts)

        return WriteReport(
            objects_written=len(objects),
            objects_linked=linked_count,
            contradictions_found=contradictions,
            ledgers_updated=sum(1 for o in objects if o.memory_type in (MemoryType.DECISION, MemoryType.ERROR)),
        )
