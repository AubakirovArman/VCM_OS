"""Tests for Exact Symbol Vault (v0.8)."""
import pytest

from vcm_os.memory.symbol_vault import (
    SymbolVaultEntry,
    SymbolVaultStore,
    SymbolVaultRetriever,
    SymbolVaultSlot,
)
from vcm_os.storage.sqlite_store import SQLiteStore


@pytest.fixture
def fresh_store(tmp_path):
    db = tmp_path / "test_symbol_vault.db"
    return SQLiteStore(db_path=db)


def test_symbol_vault_entry_roundtrip():
    entry = SymbolVaultEntry(
        project_id="proj_1",
        symbol="DATABASE_URL",
        symbol_type="env_var",
        linked_files=[".env"],
    )
    d = entry.to_dict()
    restored = SymbolVaultEntry.from_dict(d)
    assert restored.symbol == "DATABASE_URL"
    assert restored.symbol_type == "env_var"
    assert restored.linked_files == [".env"]


def test_store_upsert_and_lookup(fresh_store):
    store = SymbolVaultStore(fresh_store)
    entry = SymbolVaultEntry(
        project_id="proj_1", symbol="REDIS_URL", symbol_type="env_var"
    )
    store.upsert(entry)
    found = store.lookup("proj_1", "REDIS_URL")
    assert found is not None
    assert found.symbol_type == "env_var"


def test_store_all_for_project(fresh_store):
    store = SymbolVaultStore(fresh_store)
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="A", symbol_type="type_a"))
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="B", symbol_type="type_b"))
    store.upsert(SymbolVaultEntry(project_id="proj_2", symbol="C", symbol_type="type_c"))
    all_p1 = store.all_for_project("proj_1")
    assert len(all_p1) == 2
    symbols = {e.symbol for e in all_p1}
    assert symbols == {"A", "B"}


def test_retriever_query_match(fresh_store):
    store = SymbolVaultStore(fresh_store)
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="DATABASE_URL", symbol_type="env_var"))
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="API_KEY", symbol_type="secret"))
    retriever = SymbolVaultRetriever(store)
    hits = retriever.retrieve_for_query("proj_1", "What is the DATABASE_URL?")
    assert len(hits) == 1
    assert hits[0].symbol == "DATABASE_URL"


def test_retriever_critical_terms(fresh_store):
    store = SymbolVaultStore(fresh_store)
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="STRIPE_KEY", symbol_type="secret"))
    retriever = SymbolVaultRetriever(store)
    hits = retriever.retrieve_critical("proj_1", ["STRIPE_KEY", "MISSING"])
    assert len(hits) == 1
    assert hits[0].symbol == "STRIPE_KEY"


def test_slot_text_rendering(fresh_store):
    store = SymbolVaultStore(fresh_store)
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="FOO", symbol_type="func"))
    store.upsert(SymbolVaultEntry(project_id="proj_1", symbol="BAR", symbol_type="func"))
    slot = SymbolVaultSlot(SymbolVaultRetriever(store))
    text = slot.get_slot_text("proj_1", "query about FOO")
    assert "FOO" in text
    assert "s=FOO" in text


def test_slot_empty_when_no_matches(fresh_store):
    store = SymbolVaultStore(fresh_store)
    slot = SymbolVaultSlot(SymbolVaultRetriever(store))
    text = slot.get_slot_text("proj_1", "query about nothing")
    assert text == ""
