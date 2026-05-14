import asyncio
from typing import Any, Dict, List

from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.memory.writer import MemoryWriter
from vcm_os.session.restore import SessionRestorer
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.evals.metrics import evaluate_session_restore, recall_accuracy, token_usage
from vcm_os.verifier.consistency import ConsistencyVerifier
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.llm_client import LLMClient


class EvalHarnessV3:
    def __init__(self, writer: MemoryWriter, restorer: SessionRestorer, pack_builder: ContextPackBuilder,
                 reader: MemoryReader, scorer: MemoryScorer, verifier: ConsistencyVerifier, llm: LLMClient):
        self.writer = writer
        self.restorer = restorer
        self.pack_builder = pack_builder
        self.reader = reader
        self.scorer = scorer
        self.verifier = verifier
        self.llm = llm
        self.router = MemoryRouter()

    async def run_all(self) -> Dict[str, Dict]:
        scenarios = load_all_scenarios()
        results = {}
        for name, events in scenarios.items():
            results[name] = await self._run_scenario(name, events)
        return results

    async def _run_scenario(self, name: str, events: List[EventRecord]) -> Dict:
        # Write all events
        for ev in events:
            self.writer.capture_event(ev)

        session_id = events[-1].session_id
        project_id = events[-1].project_id

        # Test 1: Session restore
        pack = self.restorer.restore(session_id, query="Continue fixing the auth refresh loop")

        expected_goals = ["fix auth refresh", "offline"]
        expected_decisions = ["httpOnly cookie", "middleware must not refresh"]
        expected_errors = ["test failure", "refreshSession"]

        restore_metrics = evaluate_session_restore(pack, expected_goals, expected_decisions, expected_errors)
        tokens = token_usage(pack)

        # Test 2: Memory retrieval
        request = MemoryRequest(
            project_id=project_id,
            session_id=session_id,
            query="Redis connection error",
            task_type="debugging",
        )
        plan = self.router.make_plan(request)
        candidates = self.reader.retrieve(request, plan)
        scored = self.scorer.rerank(candidates, request)
        top_memories = [m.memory_id for m, _ in scored[:10]]

        # Test 3: Verifier (fake answer)
        fake_answer = "We should use SQLite instead of Redis for caching."
        verdict = self.verifier.verify_answer(
            query="What should we use for caching?",
            answer=fake_answer,
            pack=pack,
        )

        # Test 4: Query rewrite (if LLM available)
        rewritten = [request.query]
        try:
            rewritten = await self.llm.rewrite_query(request.query, request.task_type)
        except Exception:
            pass

        return {
            "restore_metrics": restore_metrics,
            "token_usage": tokens,
            "top_memories": top_memories,
            "verdict": verdict,
            "rewritten_queries": rewritten,
            "pack": pack.model_dump(),
        }

    async def run_codebase_index_test(self, directory: str, project_id: str) -> Dict:
        from vcm_os.codebase.ast_index import PythonASTIndexer
        indexer = PythonASTIndexer()
        indexer.index_directory(directory)
        return {
            "files_indexed": len(indexer.file_symbols),
            "symbols_found": len(indexer.symbols),
            "sample_symbols": [s.name for s in list(indexer.symbols.values())[:10]],
        }

    async def run_graph_expansion_test(self, project_id: str) -> Dict:
        mems = self.writer.store.get_memories(project_id=project_id, limit=10)
        if not mems:
            return {"error": "no memories"}
        from vcm_os.graph.expander import GraphExpander
        expander = GraphExpander(self.writer.store)
        expanded = expander.expand([mems[0].memory_id], max_hops=2)
        return {
            "seed": mems[0].memory_id,
            "expanded_count": len(expanded),
            "expanded_ids": [m.memory_id for m in expanded],
        }
