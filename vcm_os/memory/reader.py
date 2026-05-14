from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from vcm_os.schemas import MemoryObject, MemoryRequest, RetrievalPlan, SessionState
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.memory.reranker import Reranker
from vcm_os.graph.expander import GraphExpander


class MemoryReader:
    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
    ):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.reranker = Reranker()
        self.graph = GraphExpander(store)

    def retrieve(
        self,
        request: MemoryRequest,
        plan: RetrievalPlan,
    ) -> List[MemoryObject]:
        candidates: List[Tuple[MemoryObject, float]] = []
        vector_results: List[Tuple[str, float]] = []
        sparse_results: List[Tuple[str, float]] = []
        metadata_results: List[Tuple[str, float]] = []

        if plan.needs_session and request.session_id:
            # Session state and recent events
            state = self.store.get_session_state(request.session_id)
            if state:
                for dec_id in state.recent_decisions[-5:]:
                    mem = self.store.get_memory(dec_id)
                    if mem:
                        metadata_results.append((mem.memory_id, 1.0))
                for err_id in state.recent_errors[-5:]:
                    mem = self.store.get_memory(err_id)
                    if mem:
                        metadata_results.append((mem.memory_id, 0.95))
            session_mems = self.store.get_memories(session_id=request.session_id, limit=20)
            for m in session_mems:
                metadata_results.append((m.memory_id, 0.8))

        if plan.needs_project:
            # Vector search
            vec_results = self.vector_index.search(request.query, top_k=50)
            for mem_id, score in vec_results:
                mem = self.store.get_memory(mem_id)
                if mem and mem.project_id == request.project_id:
                    vector_results.append((mem_id, score))

            # Sparse search
            sparse_res = self.sparse_index.search(request.query, top_k=50)
            for mem_id, score in sparse_res:
                mem = self.store.get_memory(mem_id)
                if mem and mem.project_id == request.project_id:
                    sparse_results.append((mem_id, score))

        if plan.needs_decisions:
            decisions = self.store.get_memories(
                project_id=request.project_id,
                memory_type="decision",
                limit=30,
            )
            for d in decisions:
                metadata_results.append((d.memory_id, 0.9))

        if plan.needs_errors:
            errors = self.store.get_memories(
                project_id=request.project_id,
                memory_type="error",
                limit=30,
            )
            for e in errors:
                metadata_results.append((e.memory_id, 0.85))

        # Always include intents and requirements (they carry goals)
        intents = self.store.get_memories(
            project_id=request.project_id,
            memory_type="intent",
            limit=20,
        )
        for intent in intents:
            metadata_results.append((intent.memory_id, 0.75))

        requirements = self.store.get_memories(
            project_id=request.project_id,
            memory_type="requirement",
            limit=20,
        )
        for req in requirements:
            metadata_results.append((req.memory_id, 0.75))

        if plan.needs_code:
            code_changes = self.store.get_memories(
                project_id=request.project_id,
                memory_type="code_change",
                limit=15,
            )
            for c in code_changes:
                metadata_results.append((c.memory_id, 0.6))

        # RRF Fusion
        fused = self.reranker.rerank_rrf(vector_results, sparse_results, metadata_results, top_k=100)
        fused_ids = [mid for mid, _ in fused]

        # Graph expansion
        if plan.needs_graph and plan.max_graph_hops > 0:
            expanded = self.graph.expand(fused_ids[:10], max_hops=plan.max_graph_hops)
            for mem in expanded:
                if mem.memory_id not in fused_ids:
                    fused_ids.append(mem.memory_id)

        # Load memory objects and filter stale
        seen: Dict[str, MemoryObject] = {}
        for mid in fused_ids:
            mem = self.store.get_memory(mid)
            if not mem:
                continue
            if mem.validity in ("superseded", "rejected", "archived"):
                continue
            seen[mid] = mem

        # Final rerank by recency/importance/confidence with task-specific boost
        base_scores = {mid: score for mid, score in fused}
        active = self.reranker.rerank_by_recency_and_importance(
            list(seen.values()), base_scores, request.task_type
        )
        return [m for m, _ in active]
