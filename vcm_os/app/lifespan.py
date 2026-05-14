from contextlib import asynccontextmanager

from fastapi import FastAPI

import vcm_os.app.state as state
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.context.prompt_composer import PromptComposer
from vcm_os.context.sufficiency import SufficiencyChecker
from vcm_os.codebase.ast_index import PythonASTIndexer
from vcm_os.codebase.symbol_graph import SymbolGraph
from vcm_os.graph.expander import GraphExpander
from vcm_os.llm_client import LLMClient
from vcm_os.memory.decay import DecayEngine
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.reflection import ReflectionEngine
from vcm_os.memory.reranker import Reranker
from vcm_os.memory.rewriter import QueryRewriter
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.memory.writer import MemoryWriter
from vcm_os.project.code_index import CodeIndex
from vcm_os.project.decision_ledger import DecisionLedger
from vcm_os.project.error_ledger import ErrorLedger
from vcm_os.project.stale_checker import StaleChecker
from vcm_os.session.checkpoint import CheckpointManager
from vcm_os.session.restore import SessionRestorer
from vcm_os.session.store import SessionStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.summaries.generator import SummaryGenerator
from vcm_os.verifier.consistency import ConsistencyVerifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.store = SQLiteStore()
    state.vector_index = VectorIndex()
    state.sparse_index = SparseIndex()
    state.llm = LLMClient()
    state.writer = MemoryWriter(state.store, state.vector_index, state.sparse_index)
    state.reader = MemoryReader(state.store, state.vector_index, state.sparse_index)
    state.router = MemoryRouter()
    state.scorer = MemoryScorer(state.vector_index)
    state.rewriter = QueryRewriter(state.llm)
    state.reflection = ReflectionEngine(state.store, state.llm)
    state.decay = DecayEngine(state.store)
    state.session_store = SessionStore(state.store)
    state.checkpoint_manager = CheckpointManager(state.store)
    state.restorer = SessionRestorer(state.store, state.vector_index, state.sparse_index)
    state.decision_ledger = DecisionLedger(state.store)
    state.error_ledger = ErrorLedger(state.store)
    state.code_index = CodeIndex(state.store)
    state.stale_checker = StaleChecker(state.store)
    state.graph_expander = GraphExpander(state.store)
    state.pack_builder = ContextPackBuilder()
    state.prompt_composer = PromptComposer()
    state.sufficiency = SufficiencyChecker(state.llm)
    state.ast_indexer = PythonASTIndexer()
    state.symbol_graph = SymbolGraph(state.ast_indexer)
    state.verifier = ConsistencyVerifier(state.store, state.llm)
    state.summary_gen = SummaryGenerator(state.store, state.llm)
    yield
    state.vector_index.save()
    state.sparse_index.save()
    await state.llm.close()
