"""Tests for pack auto-expander."""
import tempfile

from vcm_os.context.auto_expand import PackAutoExpander
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import ContextPackSection, EventRecord, MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def test_auto_expand_no_op_when_sufficient():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    # Ingest a clear decision
    writer.capture_event(EventRecord(
        event_id="e1", project_id="p1", session_id="s1",
        event_type="assistant_response", payload={"content": "Decision: use Redis"}, raw_text="Decision: use Redis",
    ))

    reader = MemoryReader(store, vec, sparse)
    router = MemoryRouter()
    scorer = MemoryScorer(vec)
    builder = ContextPackBuilder()
    expander = PackAutoExpander(reader, router, scorer, builder)

    req = MemoryRequest(project_id="p1", query="What was the decision?", task_type="general")
    pack = expander.build_with_fallback(req)

    text = " ".join(s.content.lower() for s in pack.sections)
    assert "redis" in text


def test_auto_expand_missing_keywords():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    # Ingest about auth but query asks about database
    writer.capture_event(EventRecord(
        event_id="e1", project_id="p1", session_id="s1",
        event_type="assistant_response", payload={"content": "Decision: use JWT for auth"}, raw_text="Decision: use JWT for auth",
    ))

    reader = MemoryReader(store, vec, sparse)
    router = MemoryRouter()
    scorer = MemoryScorer(vec)
    builder = ContextPackBuilder()
    expander = PackAutoExpander(reader, router, scorer, builder)

    req = MemoryRequest(project_id="p1", query="What database should we use?", task_type="general")
    pack = expander.build_with_fallback(req)

    # Should be built even if insufficient
    assert len(pack.sections) > 0
    assert hasattr(pack, 'sufficiency_score')
