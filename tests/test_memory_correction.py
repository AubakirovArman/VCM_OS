"""Tests for memory correction service."""
import tempfile

import pytest

from vcm_os.memory.correction import CorrectionService, MemoryCorrection
from vcm_os.schemas import MemoryObject, MemoryType, SourceType, Validity
from vcm_os.storage.sqlite_store import SQLiteStore


def _make_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return SQLiteStore(f.name)


def test_apply_stale():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        validity=Validity.ACTIVE,
    ))
    corr = MemoryCorrection(memory_id="m1", action="stale", reason="Outdated")
    result = service.apply(corr)
    assert result["success"] is True
    assert result["new_validity"] == "superseded"
    mem = store.get_memory("m1")
    assert mem.validity == Validity.SUPERSEDED


def test_apply_incorrect():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        validity=Validity.ACTIVE,
    ))
    result = service.apply(MemoryCorrection(memory_id="m1", action="incorrect"))
    assert result["success"] is True
    mem = store.get_memory("m1")
    assert mem.validity == Validity.DISPUTED


def test_apply_important():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        importance_score=0.5,
    ))
    result = service.apply(MemoryCorrection(memory_id="m1", action="important"))
    assert result["success"] is True
    mem = store.get_memory("m1")
    assert mem.importance_score > 0.5
    assert mem.never_delete is True


def test_apply_pin():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    result = service.apply(MemoryCorrection(memory_id="m1", action="pin"))
    assert result["success"] is True
    mem = store.get_memory("m1")
    assert mem.never_delete is True

    result = service.apply(MemoryCorrection(memory_id="m1", action="unpin"))
    assert result["success"] is True
    mem = store.get_memory("m1")
    assert mem.never_delete is False


def test_apply_delete():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    result = service.apply(MemoryCorrection(memory_id="m1", action="delete"))
    assert result["success"] is True
    assert result["deleted"] is True
    assert store.get_memory("m1") is None


def test_correction_history():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    service.apply(MemoryCorrection(memory_id="m1", action="stale", reason="Old data"))
    service.apply(MemoryCorrection(memory_id="m1", action="important", reason="Actually critical"))
    history = service.get_correction_history("m1")
    assert len(history) == 2
    assert history[0]["action"] == "important"
    assert history[1]["action"] == "stale"


def test_review_queue():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        confidence_score=0.3,
    ))
    store.insert_memory(MemoryObject(
        memory_id="m2", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
        confidence_score=0.9,
    ))
    queue = service.get_review_queue("p1")
    assert len(queue) == 1
    assert queue[0].memory_id == "m1"


def test_correction_stats():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    service.apply(MemoryCorrection(memory_id="m1", action="stale"))
    service.apply(MemoryCorrection(memory_id="m1", action="important"))
    stats = service.get_correction_stats("p1")
    assert stats["total_corrections"] == 2
    assert stats["by_action"]["stale"] == 1
    assert stats["by_action"]["important"] == 1


def test_invalid_action():
    store = _make_store()
    service = CorrectionService(store)
    store.insert_memory(MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.USER_MESSAGE,
    ))
    result = service.apply(MemoryCorrection(memory_id="m1", action="fly_to_moon"))
    assert result["success"] is False
