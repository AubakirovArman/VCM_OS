"""Exact Symbol Vault pack slot for context builder."""
from typing import List

from vcm_os.memory.symbol_vault.schema import SymbolVaultEntry
from vcm_os.memory.symbol_vault.retrieval import SymbolVaultRetriever


class SymbolVaultSlot:
    def __init__(self, retriever: SymbolVaultRetriever):
        self.retriever = retriever

    def get_slot_text(self, project_id: str, query: str, required_terms: List[str] = None) -> str:
        """Render exact symbols as structured text for pack inclusion."""
        entries = self.retriever.retrieve_for_query(project_id, query)
        if required_terms:
            critical = self.retriever.retrieve_critical(project_id, required_terms)
            # Merge, prioritizing critical
            seen = {e.symbol for e in entries}
            for c in critical:
                if c.symbol not in seen:
                    entries.append(c)

        if not entries:
            return ""

        parts = []
        for e in entries[:3]:
            parts.append(f"s={e.symbol}")
        return " ".join(parts)
