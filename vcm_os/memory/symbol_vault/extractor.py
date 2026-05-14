"""Extract exact symbols from memory text."""
import re
from typing import List, Set

from vcm_os.memory.symbol_vault.schema import SymbolVaultEntry
from vcm_os.schemas import MemoryObject


class SymbolExtractor:
    """Extract protected exact identifiers from memory objects."""

    PATTERNS = {
        "env_var": re.compile(r"\b([A-Z_][A-Z0-9_]{3,})\b"),
        "cve": re.compile(r"\b(CVE-\d{4}-\d+)\b"),
        "package_version": re.compile(r"\b([a-zA-Z0-9_-]+>=?[\d.]+)\b"),
        "api_endpoint": re.compile(r"(/api/[a-zA-Z0-9/_-]+)"),
        "ci_job": re.compile(r"\b([a-zA-Z0-9_-]+-job)\b"),
    }

    def extract(self, memory: MemoryObject) -> List[SymbolVaultEntry]:
        """Return symbol entries found in a single memory."""
        entries = []
        text = (memory.raw_text or "") + " " + (memory.compressed_summary or "")

        for sym_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                symbol = match.group(1)
                entries.append(SymbolVaultEntry(
                    symbol=symbol,
                    symbol_type=sym_type,
                    project_id=memory.project_id,
                    source_memory_ids=[memory.memory_id],
                ))

        # Add explicit file_references as linked files
        for fp in memory.file_references:
            entries.append(SymbolVaultEntry(
                symbol=fp,
                symbol_type="file_path",
                project_id=memory.project_id,
                source_memory_ids=[memory.memory_id],
                linked_files=[fp],
            ))

        return entries

    def extract_batch(self, memories: List[MemoryObject]) -> List[SymbolVaultEntry]:
        """Deduplicate symbols across a batch of memories."""
        seen: Set[str] = set()
        results = []
        for mem in memories:
            for entry in self.extract(mem):
                key = f"{entry.project_id}::{entry.symbol}"
                if key not in seen:
                    seen.add(key)
                    results.append(entry)
        return results
