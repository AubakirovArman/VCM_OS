"""Exact Symbol Vault storage backed by SQLiteStore."""
import json
from typing import List, Optional

from vcm_os.memory.symbol_vault.schema import SymbolVaultEntry
from vcm_os.storage.sqlite_store import SQLiteStore


class SymbolVaultStore:
    def __init__(self, store: SQLiteStore):
        self.store = store
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.store._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbol_vault (
                    project_id TEXT,
                    symbol TEXT,
                    symbol_type TEXT,
                    data TEXT,
                    PRIMARY KEY (project_id, symbol)
                )
                """
            )

    def upsert(self, entry: SymbolVaultEntry) -> None:
        data = json.dumps(entry.to_dict())
        with self.store._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO symbol_vault (project_id, symbol, symbol_type, data) VALUES (?, ?, ?, ?)",
                (entry.project_id, entry.symbol, entry.symbol_type, data),
            )

    def lookup(self, project_id: str, symbol: str) -> Optional[SymbolVaultEntry]:
        with self.store._conn() as conn:
            row = conn.execute(
                "SELECT data FROM symbol_vault WHERE project_id = ? AND symbol = ?",
                (project_id, symbol),
            ).fetchone()
        if row:
            return SymbolVaultEntry.from_dict(json.loads(row[0]))
        return None

    def search_by_type(self, project_id: str, symbol_type: str) -> List[SymbolVaultEntry]:
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM symbol_vault WHERE project_id = ? AND symbol_type = ?",
                (project_id, symbol_type),
            ).fetchall()
        return [SymbolVaultEntry.from_dict(json.loads(r[0])) for r in rows]

    def all_for_project(self, project_id: str) -> List[SymbolVaultEntry]:
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM symbol_vault WHERE project_id = ?",
                (project_id,),
            ).fetchall()
        return [SymbolVaultEntry.from_dict(json.loads(r[0])) for r in rows]
