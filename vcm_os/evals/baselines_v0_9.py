"""v0.9 baselines: RawVerbatim and StrongRAG.

RawVerbatim: no LLM extraction, raw events indexed verbatim.
  Retrieval: dense + sparse + keyword + temporal + exact-symbol boost.
  Pack: chronological raw text dump.

StrongRAG: enhanced RAG with BM25, metadata filters, rerank,
  stale-aware postprocess, exact-symbol boost.
"""
from typing import Dict, List, Optional, Tuple

from vcm_os.schemas import ContextPack, ContextPackSection, MemoryObject, MemoryRequest
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.context.token_budget import TokenBudgetManager


class RawVerbatimBaseline:
    """Baseline: raw events stored verbatim, no LLM extraction.
    
    Retrieval: dense + sparse + keyword + temporal + exact-symbol boost.
    Pack: chronological raw text dump.
    """

    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
    ):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.budget = TokenBudgetManager()

    def build_pack(
        self,
        project_id: str,
        query: str,
        token_budget: int = 32768,
        required_terms: List[str] = None,
    ) -> ContextPack:
        required_terms = required_terms or []
        query_lower = query.lower()

        # 1. Dense retrieval
        vec_results = self.vector_index.search(query, top_k=30)
        vec_candidates = []
        for mem_id, score in vec_results:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id == project_id:
                vec_candidates.append((mem, score))

        # 2. Sparse retrieval (BM25)
        sparse_results = self.sparse_index.search(query, top_k=30)
        sparse_candidates = []
        for mem_id, score in sparse_results:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id == project_id:
                sparse_candidates.append((mem, score))

        # 3. Merge candidates with RRF
        merged = self._rrf_merge(vec_candidates, sparse_candidates)

        # 4. Keyword boost: bump memories containing query terms
        for mem, score in merged:
            raw = (mem.raw_text or "") + " " + (mem.compressed_summary or "")
            raw_lower = raw.lower()
            boost = 0.0
            for term in query_lower.split():
                if len(term) > 3 and term in raw_lower:
                    boost += 0.5
            score += boost

        # 5. Exact-symbol boost: bump memories containing required terms
        for mem, score in merged:
            raw = (mem.raw_text or "") + " " + (mem.compressed_summary or "")
            raw_lower = raw.lower()
            boost = 0.0
            for term in required_terms:
                if term.lower() in raw_lower:
                    boost += 2.0
            score += boost

        # 6. Temporal boost: newer memories get +0.1
        for mem, score in merged:
            if getattr(mem, "recency_score", 0) >= 0.9:
                score += 0.1

        # 7. Sort by score descending
        merged.sort(key=lambda x: x[1], reverse=True)
        top_mems = [m for m, _ in merged[:20]]

        # 8. Deduplicate by raw text hash
        seen_text = set()
        deduped = []
        for m in top_mems:
            h = hash((m.raw_text or "")[:200])
            if h not in seen_text:
                seen_text.add(h)
                deduped.append(m)

        # 9. Build pack: chronological order, no structured sections
        deduped.sort(key=lambda m: m.timestamp or "", reverse=False)

        parts = []
        used = 0
        for m in deduped:
            text = m.raw_text or m.compressed_summary or ""
            if not text:
                continue
            est = self.budget.estimate_tokens(text)
            if used + est > token_budget:
                break
            parts.append(f"[{m.memory_type or 'event'}] {text}")
            used += est

        full_text = "\n".join(parts)

        pack = ContextPack(project_id=project_id)
        pack.sections.append(ContextPackSection(
            section_name="raw_verbatim",
            content=full_text,
            memory_ids=[m.memory_id for m in deduped],
            token_estimate=used,
        ))
        pack.token_estimate = used
        return pack

    def _rrf_merge(
        self,
        vec: List[Tuple[MemoryObject, float]],
        sparse: List[Tuple[MemoryObject, float]],
    ) -> List[Tuple[MemoryObject, float]]:
        scores: Dict[str, float] = {}
        obj_map: Dict[str, MemoryObject] = {}
        for rank, (mem, _) in enumerate(vec):
            mid = mem.memory_id
            scores[mid] = scores.get(mid, 0) + 1.0 / (rank + 1 + 60)
            obj_map[mid] = mem
        for rank, (mem, _) in enumerate(sparse):
            mid = mem.memory_id
            scores[mid] = scores.get(mid, 0) + 1.0 / (rank + 1 + 60)
            obj_map[mid] = mem
        merged = [(obj_map[mid], score) for mid, score in scores.items()]
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged


class StrongRAGBaseline:
    """Baseline: enhanced RAG with BM25, metadata filters, rerank,
    stale-aware postprocess, exact-symbol boost.
    """

    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
    ):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.budget = TokenBudgetManager()

    def build_pack(
        self,
        project_id: str,
        query: str,
        token_budget: int = 32768,
        required_terms: List[str] = None,
        stale_facts: List[str] = None,
    ) -> ContextPack:
        required_terms = required_terms or []
        stale_facts = stale_facts or []

        # 1. Dense retrieval
        vec_results = self.vector_index.search(query, top_k=30)
        vec_candidates = []
        for mem_id, score in vec_results:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id == project_id:
                vec_candidates.append((mem, score))

        # 2. Sparse retrieval (BM25)
        sparse_results = self.sparse_index.search(query, top_k=30)
        sparse_candidates = []
        for mem_id, score in sparse_results:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id == project_id:
                sparse_candidates.append((mem, score))

        # 3. RRF merge
        merged = self._rrf_merge(vec_candidates, sparse_candidates)

        # 4. Rerank by exact-symbol presence
        for mem, score in merged:
            raw = (mem.raw_text or "") + " " + (mem.compressed_summary or "")
            for term in required_terms:
                if term.lower() in raw.lower():
                    score += 3.0

        # 5. Stale-aware postprocess: filter out stale/superseded
        stale_lower = [sf.lower() for sf in stale_facts]
        filtered = []
        for mem, score in merged:
            if mem.validity in ("stale", "superseded", "rejected"):
                continue
            text = (mem.raw_text or "") + " " + (mem.compressed_summary or "")
            if stale_lower and any(sf in text.lower() for sf in stale_lower):
                continue
            filtered.append((mem, score))

        filtered.sort(key=lambda x: x[1], reverse=True)
        top_mems = [m for m, _ in filtered[:15]]

        # 6. Build pack with structured sections
        parts = []
        used = 0
        for m in top_mems:
            text = m.compressed_summary or m.raw_text or ""
            if not text:
                continue
            est = self.budget.estimate_tokens(text)
            if used + est > token_budget:
                break
            parts.append(f"[{m.memory_type or 'event'}] {text}")
            used += est

        full_text = "\n".join(parts)

        pack = ContextPack(project_id=project_id)
        pack.sections.append(ContextPackSection(
            section_name="strong_rag",
            content=full_text,
            memory_ids=[m.memory_id for m in top_mems],
            token_estimate=used,
        ))
        pack.token_estimate = used
        return pack

    def _rrf_merge(
        self,
        vec: List[Tuple[MemoryObject, float]],
        sparse: List[Tuple[MemoryObject, float]],
    ) -> List[Tuple[MemoryObject, float]]:
        scores: Dict[str, float] = {}
        obj_map: Dict[str, MemoryObject] = {}
        for rank, (mem, _) in enumerate(vec):
            mid = mem.memory_id
            scores[mid] = scores.get(mid, 0) + 1.0 / (rank + 1 + 60)
            obj_map[mid] = mem
        for rank, (mem, _) in enumerate(sparse):
            mid = mem.memory_id
            scores[mid] = scores.get(mid, 0) + 1.0 / (rank + 1 + 60)
            obj_map[mid] = mem
        merged = [(obj_map[mid], score) for mid, score in scores.items()]
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged
