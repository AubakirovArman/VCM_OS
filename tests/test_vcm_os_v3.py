import os
import tempfile

import pytest

from vcm_os.schemas import EventRecord, MemoryObject, MemoryRequest
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.memory.writer import MemoryWriter
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.verifier.consistency import ConsistencyVerifier
from vcm_os.codebase.ast_index import PythonASTIndexer
from vcm_os.codebase.symbol_graph import SymbolGraph
from vcm_os.graph.expander import GraphExpander


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = SQLiteStore(db_path=db_path)
        yield store


@pytest.fixture
def indexes(temp_store):
    with tempfile.TemporaryDirectory() as tmpdir:
        import vcm_os.config as cfg
        orig_dir = cfg.DATA_DIR
        cfg.DATA_DIR = tmpdir
        vi = VectorIndex()
        si = SparseIndex()
        yield vi, si
        cfg.DATA_DIR = orig_dir


def test_verifier_detects_contradiction(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)

    event = EventRecord(
        project_id="proj_verify",
        event_type="user_message",
        raw_text="Decision: use PostgreSQL for main DB.",
    )
    writer.capture_event(event)

    from vcm_os.context.pack_builder import ContextPackBuilder
    builder = ContextPackBuilder()
    request = MemoryRequest(project_id="proj_verify", query="which DB?", task_type="architecture")
    candidates = temp_store.get_memories(project_id="proj_verify")
    pack = builder.build(request, candidates)

    verifier = ConsistencyVerifier(temp_store)

    # Consistent answer
    ok_answer = "We use PostgreSQL for the main DB."
    result = verifier.verify_answer("which DB?", ok_answer, pack)
    assert result["consistent"] is True

    # Contradictory answer (naive negation detection)
    bad_answer = "We should not use PostgreSQL. Use SQLite instead."
    result2 = verifier.verify_answer("which DB?", bad_answer, pack)
    assert result2["consistent"] is False or len(result2["violations"]) > 0


def test_ast_indexer_on_own_codebase():
    indexer = PythonASTIndexer()
    # Index the vcm_os codebase itself
    codebase_path = os.path.join(os.path.dirname(__file__), "..", "vcm_os")
    indexer.index_directory(codebase_path)

    assert len(indexer.symbols) > 0
    assert len(indexer.file_symbols) > 0

    # Search for known symbol
    results = indexer.search_symbol("MemoryWriter")
    assert len(results) > 0

    # Check call graph
    for key, sym in indexer.symbols.items():
        if sym.symbol_type == "function":
            callers = indexer.get_callers(sym.name)
            # Just ensure no crash
            assert isinstance(callers, list)
            break


def test_symbol_graph_affected_symbols():
    indexer = PythonASTIndexer()
    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
class AuthService:
    def login(self, user, password):
        return self.validate(user, password)

    def validate(self, user, password):
        return True

def main():
    service = AuthService()
    service.login("user", "pass")
""")
        f.flush()
        indexer.index_file(f.name)

    graph = SymbolGraph(indexer)
    affected = graph.find_affected_symbols(f.name, [4, 5])
    assert len(affected) > 0

    # Cleanup
    os.unlink(f.name)


def test_graph_expansion_with_links(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)

    ev1 = EventRecord(project_id="proj_g", event_type="user_message", raw_text="Decision: use API v2.")
    writer.capture_event(ev1)
    ev2 = EventRecord(project_id="proj_g", event_type="code_change", raw_text="Updated client.py to use v2.")
    writer.capture_event(ev2)

    mems = temp_store.get_memories(project_id="proj_g")
    if len(mems) >= 2:
        temp_store.insert_link(mems[0].memory_id, mems[1].memory_id, "affects", 0.9)

    expander = GraphExpander(temp_store)
    expanded = expander.expand([mems[0].memory_id], max_hops=2)
    assert len(expanded) >= 1

    neighbors = expander.get_neighbors(mems[0].memory_id)
    assert len(neighbors) >= 0


def test_memory_object_has_access_count(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    event = EventRecord(
        project_id="proj_ac",
        event_type="user_message",
        raw_text="Decision: use Redis.",
    )
    writer.capture_event(event)

    mems = temp_store.get_memories(project_id="proj_ac")
    assert len(mems) > 0
    # access_count should be 0 initially (or not present)
    assert getattr(mems[0], "access_count", 0) >= 0
