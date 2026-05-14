"""Tests for verifier repair loop."""
import tempfile

from vcm_os.context.auto_expand import PackAutoExpander
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import ContextPack, ContextPackSection, EventRecord, MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.verifier.repair_loop import VerifierRepairLoop


def test_repair_loop_pass():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    writer.capture_event(EventRecord(
        event_id="e1", project_id="p1", session_id="s1",
        event_type="assistant_response", payload={"content": "Decision: use Redis"}, raw_text="Decision: use Redis",
    ))

    reader = MemoryReader(store, vec, sparse)
    router = MemoryRouter()
    scorer = MemoryScorer(vec)
    builder = ContextPackBuilder()
    expander = PackAutoExpander(reader, router, scorer, builder)
    repair = VerifierRepairLoop(expander)

    req = MemoryRequest(project_id="p1", query="What was the decision?", task_type="general")
    pack = expander.build_with_fallback(req)

    result = repair.verify_and_repair(
        "We decided to use Redis. This is based on project memory.",
        req, pack, [],
    )
    assert result["status"] == "pass"
    assert result["repairs"] == []


def test_repair_loop_stale_flagged():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()

    from vcm_os.schemas import MemoryObject, MemoryType, SourceType, Validity
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        raw_text="We should use MySQL database", compressed_summary="We should use MySQL database",
        validity=Validity.SUPERSEDED,
    ))

    reader = MemoryReader(store, vec, sparse)
    router = MemoryRouter()
    scorer = MemoryScorer(vec)
    builder = ContextPackBuilder()
    expander = PackAutoExpander(reader, router, scorer, builder)
    repair = VerifierRepairLoop(expander)

    req = MemoryRequest(project_id="p1", query="What database?", task_type="general")
    pack = ContextPack(
        project_id="p1",
        sections=[ContextPackSection(section_name="facts", content="We should use MySQL database", source_memory_id="m1")],
    )
    memories = [store.get_memory("m1")]

    result = repair.verify_and_repair(
        "We should use MySQL database.",
        req, pack, memories,
    )
    assert result["status"] == "fail"
    assert any(r["type"] == "stale_flagged" for r in result["repairs"])
