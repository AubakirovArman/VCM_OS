"""Project State Object storage backed by SQLiteStore."""
import json
from typing import Optional

from vcm_os.memory.project_state.schema import ProjectStateObject
from vcm_os.storage.sqlite_store import SQLiteStore


class ProjectStateStore:
    """Store and retrieve PSO snapshots."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.store._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_state (
                    project_id TEXT PRIMARY KEY,
                    version INTEGER,
                    updated_at TEXT,
                    data TEXT
                )
                """
            )

    def save(self, pso: ProjectStateObject) -> None:
        data = json.dumps(pso.to_dict())
        with self.store._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_state (project_id, version, updated_at, data) VALUES (?, ?, ?, ?)",
                (pso.project_id, pso.version, pso.updated_at, data),
            )

    def load(self, project_id: str) -> Optional[ProjectStateObject]:
        with self.store._conn() as conn:
            row = conn.execute(
                "SELECT data FROM project_state WHERE project_id = ?", (project_id,)
            ).fetchone()
        if row:
            return ProjectStateObject.from_dict(json.loads(row[0]))
        return None
