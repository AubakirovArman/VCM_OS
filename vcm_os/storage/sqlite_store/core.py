import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from vcm_os.config import DB_PATH
from vcm_os.schemas import (
    DecisionEntry,
    EntityRef,
    ErrorEntry,
    EventRecord,
    MemoryObject,
    SessionCheckpoint,
    SessionIdentity,
    SessionState,
    SourcePointer,
)




class SQLiteStoreCore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "event_id TEXT PRIMARY KEY, session_id TEXT, project_id TEXT NOT NULL, "
                "timestamp TEXT NOT NULL, event_type TEXT NOT NULL, payload TEXT, raw_text TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_objects ("
                "memory_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, session_id TEXT, "
                "user_id TEXT, timestamp TEXT NOT NULL, memory_type TEXT NOT NULL, "
                "source_type TEXT NOT NULL, source_pointer TEXT, raw_text TEXT, "
                "compressed_summary TEXT, semantic_summary TEXT, entities TEXT, intents TEXT, "
                "decisions TEXT, constraints TEXT, assumptions TEXT, open_questions TEXT, "
                "code_references TEXT, file_references TEXT, tools_used TEXT, errors_found TEXT, "
                "lessons_learned TEXT, importance_score REAL, recency_score REAL, "
                "confidence_score REAL, stability TEXT, validity TEXT, evidence_strength TEXT, "
                "contradiction_links TEXT, dependency_links TEXT, parent_memory_id TEXT, "
                "child_memory_ids TEXT, graph_node_ids TEXT, embedding_vector TEXT, "
                "embedding_model TEXT, access_scope TEXT, cross_session INTEGER, "
                "cross_project INTEGER, ttl_days INTEGER, decay_policy TEXT, "
                "never_delete INTEGER, version INTEGER, schema_version TEXT, audit_log TEXT)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_project ON memory_objects(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_session ON memory_objects(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_type ON memory_objects(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_validity ON memory_objects(validity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_timestamp ON memory_objects(timestamp)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "session_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT, "
                "created_at TEXT NOT NULL, last_active_at TEXT NOT NULL, status TEXT, "
                "branch TEXT, workspace_root TEXT, active_goal_ids TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS session_states ("
                "session_id TEXT PRIMARY KEY, active_goals TEXT, active_files TEXT, "
                "current_plan TEXT, open_tasks TEXT, recent_decisions TEXT, "
                "recent_errors TEXT, current_code_branch TEXT, tool_state TEXT, "
                "unresolved_assumptions TEXT, last_checkpoint_id TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS checkpoints ("
                "checkpoint_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, "
                "project_id TEXT NOT NULL, timestamp TEXT NOT NULL, state TEXT, packed_summary TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS decisions ("
                "decision_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, session_id TEXT, "
                "timestamp TEXT NOT NULL, decision_text TEXT, status TEXT, confidence REAL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS errors ("
                "error_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, session_id TEXT, "
                "timestamp TEXT NOT NULL, error_text TEXT, error_kind TEXT, status TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_links ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, "
                "target_id TEXT NOT NULL, relation_type TEXT, confidence REAL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS stale_markers ("
                "memory_id TEXT PRIMARY KEY, reason TEXT, marked_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS canonical_hashes ("
                "project_id TEXT NOT NULL, session_id TEXT, memory_type TEXT NOT NULL, "
                "content_hash TEXT NOT NULL, "
                "PRIMARY KEY (project_id, session_id, memory_type, content_hash))"
            )
        self.run_migrations()

    def run_migrations(self) -> List[str]:
        # Apply pending migrations. Returns list of applied versions.
        migrations: Dict[str, str] = {
            "001_add_memory_links": (
                "CREATE TABLE IF NOT EXISTS memory_links ("
                "source_id TEXT NOT NULL, target_id TEXT NOT NULL, "
                "relation_type TEXT NOT NULL, confidence REAL DEFAULT 1.0, "
                "PRIMARY KEY (source_id, target_id, relation_type))"
            ),
            "002_add_stale_markers": (
                "CREATE TABLE IF NOT EXISTS stale_markers ("
                "memory_id TEXT PRIMARY KEY, reason TEXT, marked_at TEXT NOT NULL)"
            ),
            "003_add_canonical_hashes": (
                "CREATE TABLE IF NOT EXISTS canonical_hashes ("
                "project_id TEXT NOT NULL, session_id TEXT, "
                "memory_type TEXT NOT NULL, content_hash TEXT NOT NULL, "
                "PRIMARY KEY (project_id, session_id, memory_type, content_hash))"
            ),
            "004_add_memory_corrections": (
                "CREATE TABLE IF NOT EXISTS memory_corrections ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, memory_id TEXT NOT NULL, "
                "action TEXT NOT NULL, reason TEXT, user_id TEXT, timestamp TEXT NOT NULL)"
            ),
        }
        applied = []
        with self._conn() as conn:
            existing = set(
                r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
            )
            for version, sql in migrations.items():
                if version not in existing:
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (version, datetime.now(timezone.utc).isoformat()),
                    )
                    applied.append(version)
        return applied