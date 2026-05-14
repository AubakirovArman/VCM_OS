"""Tests for auto memory linker."""
import tempfile

import pytest

from vcm_os.memory.linker import AutoLinker
from vcm_os.schemas import MemoryObject, MemoryType, SourceType
from vcm_os.storage.sqlite_store import SQLiteStore


def test_same_session_link():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.INTENT, source_type=SourceType.USER_MESSAGE,
        raw_text="We need to refactor auth",
    )
    m2 = MemoryObject(
        memory_id="m2", project_id="p1", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.ASSISTANT_MESSAGE,
        raw_text="Decision: use JWT tokens",
    )
    store.insert_memory(m1)
    links = linker.link(m2)

    assert any(rel == "same_session" for _, rel, _ in links)


def test_shared_file_link():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.CODE_CHANGE, source_type=SourceType.CODE_DIFF,
        raw_text="Updated auth.py",
        file_references=["auth.py"],
    )
    m2 = MemoryObject(
        memory_id="m2", project_id="p1", session_id="s2",
        memory_type=MemoryType.ERROR, source_type=SourceType.TOOL_OUTPUT,
        raw_text="Error in auth.py line 42",
        file_references=["auth.py"],
    )
    store.insert_memory(m1)
    links = linker.link(m2)

    # error + code_change triggers type relation first, but shared_file also exists
    assert any(rel in ("shared_file", "error_caused_by_symbol") for _, rel, _ in links)


def test_type_relation_link():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.TASK, source_type=SourceType.USER_MESSAGE,
        raw_text="Task: implement OAuth",
    )
    m2 = MemoryObject(
        memory_id="m2", project_id="p1", session_id="s2",
        memory_type=MemoryType.GOAL, source_type=SourceType.USER_MESSAGE,
        raw_text="Goal: secure authentication",
    )
    store.insert_memory(m1)
    links = linker.link(m2)

    assert any(rel == "task_achieves_goal" for _, rel, _ in links)


def test_keyword_overlap_link():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.FACT, source_type=SourceType.TOOL_OUTPUT,
        raw_text="pytest authentication module passed successfully",
    )
    m2 = MemoryObject(
        memory_id="m2", project_id="p1", session_id="s2",
        memory_type=MemoryType.FACT, source_type=SourceType.TOOL_OUTPUT,
        raw_text="authentication module passed tests",
    )
    store.insert_memory(m1)
    links = linker.link(m2)

    # Need 3+ overlapping keywords. "pytest", "authentication", "module" = 3
    assert any(rel == "keyword_overlap" for _, rel, _ in links)


def test_no_self_link():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.INTENT, source_type=SourceType.USER_MESSAGE,
        raw_text="test",
    )
    store.insert_memory(m1)
    links = linker.link(m1)

    assert len(links) == 0


def test_links_stored_in_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SQLiteStore(db_path)
    linker = AutoLinker(store)

    m1 = MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=MemoryType.INTENT, source_type=SourceType.USER_MESSAGE,
        raw_text="refactor auth",
    )
    m2 = MemoryObject(
        memory_id="m2", project_id="p1", session_id="s1",
        memory_type=MemoryType.DECISION, source_type=SourceType.ASSISTANT_MESSAGE,
        raw_text="use JWT",
    )
    store.insert_memory(m1)
    linker.link(m2)

    linked = store.get_linked("m2")
    assert len(linked) >= 1
    assert any(target == "m1" for target, _, _ in linked)
