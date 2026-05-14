"""Tests for cross-project memory transfer."""
import tempfile

from vcm_os.memory.cross_project import CrossProjectTransfer
from vcm_os.schemas import MemoryObject, MemoryType, SourceType, Validity
from vcm_os.storage.sqlite_store import SQLiteStore


def test_find_similar_projects():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    transfer = CrossProjectTransfer(store)

    # Project A: auth + caching
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="proj_a", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use Redis for caching", validity=Validity.ACTIVE,
        file_references=["src/cache.py"],
    ))
    store.insert_memory(MemoryObject(
        memory_id="m2", project_id="proj_a", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use JWT for auth", validity=Validity.ACTIVE,
        file_references=["src/auth.py"],
    ))

    # Project B: auth + database (some overlap with A)
    store.insert_memory(MemoryObject(
        memory_id="m3", project_id="proj_b", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use JWT for auth", validity=Validity.ACTIVE,
        file_references=["src/auth.py"],
    ))
    store.insert_memory(MemoryObject(
        memory_id="m4", project_id="proj_b", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use PostgreSQL", validity=Validity.ACTIVE,
        file_references=["src/db.py"],
    ))

    # Project C: completely different
    store.insert_memory(MemoryObject(
        memory_id="m5", project_id="proj_c", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use React for frontend", validity=Validity.ACTIVE,
        file_references=["src/app.tsx"],
    ))

    similar = transfer.find_similar_projects("proj_a")
    pids = [pid for pid, _ in similar]
    assert "proj_b" in pids  # Should be similar (shared auth/JWT)
    assert "proj_c" not in pids  # Should not be similar


def test_get_transferable_memories():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    transfer = CrossProjectTransfer(store)

    # Source project
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="proj_src", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use Redis for caching", validity=Validity.ACTIVE,
    ))
    store.insert_memory(MemoryObject(
        memory_id="m2", project_id="proj_src", session_id="s1",
        memory_type=MemoryType.ERROR, source_type=SourceType.USER_MESSAGE,
        raw_text="Error: Redis memory leak", validity=Validity.ACTIVE,
    ))

    # Similar project
    store.insert_memory(MemoryObject(
        memory_id="m3", project_id="proj_sim", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use Redis for session store", validity=Validity.ACTIVE,
    ))
    store.insert_memory(MemoryObject(
        memory_id="m4", project_id="proj_sim", session_id="s1",
        memory_type=MemoryType.ERROR, source_type=SourceType.USER_MESSAGE,
        raw_text="Error: Redis connection timeout", validity=Validity.ACTIVE,
    ))

    warnings = transfer.get_transferable_memories("proj_src", query="Redis")
    assert len(warnings) > 0
    assert any("Redis" in w["summary"] for w in warnings)
    assert all(w["source_project"] == "proj_sim" for w in warnings)


def test_no_similar_projects():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    transfer = CrossProjectTransfer(store)

    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="proj_a", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        raw_text="Decision: use Redis", validity=Validity.ACTIVE,
    ))

    similar = transfer.find_similar_projects("proj_a")
    assert len(similar) == 0

    warnings = transfer.get_transferable_memories("proj_a")
    assert len(warnings) == 0
