"""Tests for production dashboard."""
import tempfile

from vcm_os.dashboard.metrics import DashboardMetrics
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import EventRecord, MemoryObject, MemoryType, SourceType
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


def test_dashboard_snapshot():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)

    # Add some data
    for i in range(3):
        writer.capture_event(EventRecord(
            event_id=f"e{i}", project_id="p1", session_id="s1",
            event_type="user_message", payload={"content": f"msg {i}"}, raw_text=f"msg {i}",
        ))

    metrics = DashboardMetrics(store, vec, sparse)
    snap = metrics.snapshot()

    assert "timestamp" in snap
    assert "health" in snap
    assert "latency" in snap
    assert "retrieval" in snap
    assert "errors" in snap
    assert snap["version"] == "0.5.0"

    health = snap["health"]
    assert health["basic"]["memories"] > 0
    assert health["basic"]["projects"] == 1

    retrieval = snap["retrieval"]
    assert retrieval["total_memories"] > 0
    assert retrieval["link_ratio"] <= 1.0  # Some may be linked


def test_dashboard_error_metrics():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    vec = VectorIndex()
    sparse = SparseIndex()

    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.ERROR, source_type=SourceType.TOOL_OUTPUT,
        raw_text="Error: timeout", validity="active",
    ))
    store.insert_memory(MemoryObject(
        memory_id="m2", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        raw_text="Fact", validity="disputed",
    ))

    metrics = DashboardMetrics(store, vec, sparse)
    errors = metrics._error_metrics()
    assert errors["recent_errors_24h"] >= 1
    assert errors["disputed_memories"] == 1
