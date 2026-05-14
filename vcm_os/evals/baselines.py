from typing import Dict, List, Tuple

from vcm_os.schemas import ContextPack, ContextPackSection, MemoryObject, MemoryRequest
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.memory.writer import MemoryWriter
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.context.token_budget import TokenBudgetManager


class SummaryBaseline:
    """Baseline: realistic human summary — only decisions and errors, heavily compressed."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.budget = TokenBudgetManager()

    def build_pack(self, project_id: str, query: str, token_budget: int = 32768) -> ContextPack:
        # Only include decisions and errors (human summaries typically lose events/code/requirements)
        decisions = self.store.get_memories(project_id=project_id, memory_type="decision", limit=20)
        errors = self.store.get_memories(project_id=project_id, memory_type="error", limit=10)

        parts = []
        for d in decisions:
            text = d.compressed_summary or d.raw_text or ""
            if text:
                # Heavy compression: first 10 words only
                words = text.split()[:10]
                parts.append(" ".join(words))
        for e in errors:
            text = e.compressed_summary or e.raw_text or ""
            if text:
                words = text.split()[:8]
                parts.append(" ".join(words))

        full_text = "\n".join(parts)
        max_chars = token_budget * 3
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n...[truncated]"

        pack = ContextPack(project_id=project_id)
        pack.sections.append(ContextPackSection(
            section_name="summary",
            content=full_text,
            memory_ids=[],
            token_estimate=self.budget.estimate_tokens(full_text),
        ))
        pack.token_estimate = pack.sections[0].token_estimate
        return pack


class RAGBaseline:
    """Baseline: vector search only, no structured memory, no ledgers, no session state."""

    def __init__(self, store: SQLiteStore, vector_index: VectorIndex):
        self.store = store
        self.vector_index = vector_index
        self.pack_builder = ContextPackBuilder()

    def build_pack(self, project_id: str, query: str, token_budget: int = 32768) -> ContextPack:
        vec_results = self.vector_index.search(query, top_k=20)
        candidates = []
        for mem_id, score in vec_results:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id == project_id:
                candidates.append(mem)

        request = MemoryRequest(project_id=project_id, query=query, token_budget=token_budget)
        return self.pack_builder.build(request, candidates)


class FullContextBaseline:
    """Baseline: dump ALL memories into context."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.budget = TokenBudgetManager()

    def build_pack(self, project_id: str, query: str, token_budget: int = 32768) -> ContextPack:
        mems = self.store.get_memories(project_id=project_id, limit=10000)
        parts = []
        for m in mems:
            text = m.compressed_summary or m.raw_text or ""
            if text:
                parts.append(f"[{m.memory_type}] {text[:400]}")

        full_text = "\n\n".join(parts)
        max_chars = token_budget * 3
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n...[truncated]"

        pack = ContextPack(project_id=project_id)
        pack.sections.append(ContextPackSection(
            section_name="full_context",
            content=full_text,
            memory_ids=[m.memory_id for m in mems],
            token_estimate=self.budget.estimate_tokens(full_text),
        ))
        pack.token_estimate = pack.sections[0].token_estimate
        return pack
