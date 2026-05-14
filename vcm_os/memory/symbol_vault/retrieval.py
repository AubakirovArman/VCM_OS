"""Exact symbol retrieval from vault."""
from typing import List

from vcm_os.memory.symbol_vault.schema import SymbolVaultEntry
from vcm_os.memory.symbol_vault.store import SymbolVaultStore


class SymbolVaultRetriever:
    """Retrieve exact symbols that match query terms or are critical."""

    def __init__(self, store: SymbolVaultStore):
        self.store = store

    def retrieve_for_query(self, project_id: str, query: str) -> List[SymbolVaultEntry]:
        """Find symbols mentioned in query."""
        query_lower = query.lower()
        all_symbols = self.store.all_for_project(project_id)
        hits = []
        for entry in all_symbols:
            if entry.symbol.lower() in query_lower:
                hits.append(entry)
        return hits

    def retrieve_critical(self, project_id: str, required_terms: List[str]) -> List[SymbolVaultEntry]:
        """Find symbols matching required critical terms."""
        hits = []
        for term in required_terms:
            entry = self.store.lookup(project_id, term)
            if entry:
                hits.append(entry)
        return hits
