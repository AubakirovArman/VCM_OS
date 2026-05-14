"""Exact Symbol Vault schema."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SymbolVaultEntry:
    symbol: str
    symbol_type: str  # env_var, api_endpoint, cve, package_version, config_key, ci_job, function_name
    project_id: str
    source_memory_ids: List[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    linked_decisions: List[str] = field(default_factory=list)
    linked_files: List[str] = field(default_factory=list)
    must_preserve: bool = True

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "symbol_type": self.symbol_type,
            "project_id": self.project_id,
            "source_memory_ids": self.source_memory_ids,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "linked_decisions": self.linked_decisions,
            "linked_files": self.linked_files,
            "must_preserve": self.must_preserve,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SymbolVaultEntry":
        return cls(
            symbol=d.get("symbol", ""),
            symbol_type=d.get("symbol_type", ""),
            project_id=d.get("project_id", ""),
            source_memory_ids=d.get("source_memory_ids", []),
            first_seen=d.get("first_seen", ""),
            last_seen=d.get("last_seen", ""),
            linked_decisions=d.get("linked_decisions", []),
            linked_files=d.get("linked_files", []),
            must_preserve=d.get("must_preserve", True),
        )
