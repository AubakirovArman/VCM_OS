"""Tests for memory health dashboard."""
import tempfile

import pytest

from vcm_os.health.dashboard import MemoryHealthDashboard
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryObject, MemoryType, SourceType, Validity
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def test_dashboard_basic_counts():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    # Insert some events
    for i in range(3):
        writer.capture_event(EventRecord(
            event_id=f"e{i}", project_id="p1", session_id="s1",
            event_type="user_message", payload={"content": f"msg {i}"}, raw_text=f"msg {i}",
        ))

    dashboard = MemoryHealthDashboard(store)
    snap = dashboard.snapshot()
    assert snap["basic"]["events"] == 3
    assert snap["basic"]["memories"] > 0
    assert snap["basic"]["projects"] == 1
    assert snap["basic"]["sessions"] == 1
    assert 0.0 <= snap["score"] <= 1.0


def test_dashboard_validity_distribution():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        validity=Validity.ACTIVE,
    ))
    store.insert_memory(MemoryObject(
        memory_id="m2", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        validity=Validity.ARCHIVED,
    ))
    dashboard = MemoryHealthDashboard(store)
    snap = dashboard.snapshot()
    assert snap["validity"].get("active", 0) == 1
    assert snap["validity"].get("archived", 0) == 1


def test_dashboard_orphaned_memories():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    dashboard = MemoryHealthDashboard(store)
    snap = dashboard.snapshot()
    assert snap["orphans"]["count"] == 1
    assert snap["orphans"]["ratio"] == 1.0


def test_dashboard_recent_activity():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    writer = MemoryWriter(store, VectorIndex(), SparseIndex())
    for i in range(2):
        writer.capture_event(EventRecord(
            event_id=f"e{i}", project_id="p1", session_id="s1",
            event_type="user_message", payload={"content": f"msg {i}"}, raw_text=f"msg {i}",
        ))
    dashboard = MemoryHealthDashboard(store)
    snap = dashboard.snapshot()
    assert snap["recent_activity"]["last_24h"] == 2


def test_dashboard_duplicate_detection():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    # Same hash across different sessions = duplicate content
    store.add_canonical_hash("p1", "s1", "fact", "abc123")
    store.add_canonical_hash("p1", "s2", "fact", "abc123")
    store.add_canonical_hash("p1", "s1", "fact", "def456")
    dashboard = MemoryHealthDashboard(store)
    snap = dashboard.snapshot()
    assert snap["duplicates"]["duplicate_groups"] == 1
    assert snap["duplicates"]["duplicate_memories"] == 2
    assert snap["duplicates"]["has_duplicates"] is True
