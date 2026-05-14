import os
import tempfile

import pytest

from vcm_os.schemas import EventRecord, MemoryObject, MemoryRequest, SessionState
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.memory.writer import MemoryWriter
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.reranker import Reranker, reciprocal_rank_fusion
from vcm_os.memory.decay import DecayEngine
from vcm_os.graph.expander import GraphExpander
from vcm_os.project.stale_checker import StaleChecker
from vcm_os.context.pack_builder import ContextPackBuilder


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


def test_rrf_fusion():
    vec = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
    sparse = [("b", 0.85), ("c", 0.75), ("d", 0.6)]
    meta = [("a", 1.0), ("d", 0.5)]
    fused = reciprocal_rank_fusion([vec, sparse, meta])
    ids = [mid for mid, _ in fused]
    assert "a" in ids
    assert "b" in ids
    assert "c" in ids
    assert "d" in ids


def test_reranker_by_recency(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    event = EventRecord(
        project_id="proj_rerank",
        event_type="user_message",
        raw_text="Decision: use Kafka for messaging.",
    )
    writer.capture_event(event)

    mems = temp_store.get_memories(project_id="proj_rerank")
    assert len(mems) > 0

    reranker = Reranker()
    scores = {m.memory_id: 0.5 for m in mems}
    result = reranker.rerank_by_recency_and_importance(mems, scores)
    assert len(result) == len(mems)
    assert result[0][1] > 0


def test_graph_expansion(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)

    ev1 = EventRecord(project_id="proj_graph", event_type="user_message", raw_text="Decision: use Postgres.")
    writer.capture_event(ev1)
    ev2 = EventRecord(project_id="proj_graph", event_type="code_change", raw_text="Created db.py", payload={"file_path": "db.py"})
    writer.capture_event(ev2)

    mems = temp_store.get_memories(project_id="proj_graph")
    # Manually link them
    if len(mems) >= 2:
        temp_store.insert_link(mems[0].memory_id, mems[1].memory_id, "related", 0.9)

    expander = GraphExpander(temp_store)
    expanded = expander.expand([mems[0].memory_id], max_hops=2)
    assert len(expanded) >= 1


def test_decay_engine(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    event = EventRecord(
        project_id="proj_decay",
        event_type="user_message",
        raw_text="Decision: use old library v1.",
    )
    writer.capture_event(event)

    decay = DecayEngine(temp_store)
    stats = decay.run_decay("proj_decay")
    assert "unchanged" in stats


def test_stale_checker(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    event = EventRecord(
        project_id="proj_stale",
        event_type="code_change",
        raw_text="Created file",
        payload={"file_path": "nonexistent.py"},
    )
    writer.capture_event(event)

    checker = StaleChecker(temp_store)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = checker.flag_stale_memories("proj_stale", workspace_root=tmpdir)
        assert "code" in result
        assert len(result["code"]) > 0


def test_context_pack_adaptive_compression(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    for i in range(10):
        event = EventRecord(
            project_id="proj_pack",
            event_type="user_message",
            raw_text=f"Decision {i}: use service {i}.",
        )
        writer.capture_event(event)

    builder = ContextPackBuilder()
    request = MemoryRequest(
        project_id="proj_pack",
        query="which service",
        task_type="architecture",
        token_budget=4000,
    )
    candidates = temp_store.get_memories(project_id="proj_pack", limit=50)
    pack = builder.build(request, candidates)
    assert pack.token_estimate <= request.token_budget * 1.1
    assert any(s.section_name == "decisions" for s in pack.sections)
