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




class MemoryStoreMixin:

    def insert_memory(self, mem: MemoryObject) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memory_objects ("
                "memory_id, project_id, session_id, user_id, timestamp, memory_type, source_type, "
                "source_pointer, raw_text, compressed_summary, semantic_summary, entities, intents, "
                "decisions, constraints, assumptions, open_questions, code_references, file_references, "
                "tools_used, errors_found, lessons_learned, importance_score, recency_score, "
                "confidence_score, stability, validity, evidence_strength, contradiction_links, "
                "dependency_links, parent_memory_id, child_memory_ids, graph_node_ids, "
                "embedding_vector, embedding_model, access_scope, cross_session, cross_project, "
                "ttl_days, decay_policy, never_delete, version, schema_version, audit_log) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._mem_to_tuple(mem),
            )

    def update_memory(self, mem: MemoryObject) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE memory_objects SET "
                "project_id=?, session_id=?, user_id=?, timestamp=?, memory_type=?, source_type=?, "
                "source_pointer=?, raw_text=?, compressed_summary=?, semantic_summary=?, entities=?, "
                "intents=?, decisions=?, constraints=?, assumptions=?, open_questions=?, "
                "code_references=?, file_references=?, tools_used=?, errors_found=?, "
                "lessons_learned=?, importance_score=?, recency_score=?, confidence_score=?, "
                "stability=?, validity=?, evidence_strength=?, contradiction_links=?, "
                "dependency_links=?, parent_memory_id=?, child_memory_ids=?, graph_node_ids=?, "
                "embedding_vector=?, embedding_model=?, access_scope=?, cross_session=?, "
                "cross_project=?, ttl_days=?, decay_policy=?, never_delete=?, version=?, "
                "schema_version=?, audit_log=? WHERE memory_id=?",
                self._mem_to_tuple(mem)[1:] + (mem.memory_id,),
            )

    def get_memory(self, memory_id: str) -> Optional[MemoryObject]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memory_objects WHERE memory_id = ?", (memory_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def delete_memory(self, memory_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM memory_links WHERE source_id = ? OR target_id = ?", (memory_id, memory_id))
            conn.execute("DELETE FROM memory_objects WHERE memory_id = ?", (memory_id,))

    def get_memories(
        self,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        validity: Optional[str] = None,
        limit: int = 1000,
    ) -> List[MemoryObject]:
        query = "SELECT * FROM memory_objects WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        if validity:
            query += " AND validity = ?"
            params.append(validity)
        query += " ORDER BY recency_score DESC, importance_score DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def _mem_to_tuple(self, mem: MemoryObject) -> Tuple:
        return (
            mem.memory_id,
            mem.project_id,
            mem.session_id,
            mem.user_id,
            mem.timestamp.isoformat(),
            mem.memory_type,
            mem.source_type,
            json.dumps(mem.source_pointer.model_dump()) if mem.source_pointer else None,
            mem.raw_text,
            mem.compressed_summary,
            mem.semantic_summary,
            json.dumps([e.model_dump() for e in mem.entities]) if mem.entities else None,
            json.dumps(mem.intents) if mem.intents else None,
            json.dumps([d.model_dump() for d in mem.decisions]) if mem.decisions else None,
            json.dumps(mem.constraints) if mem.constraints else None,
            json.dumps(mem.assumptions) if mem.assumptions else None,
            json.dumps(mem.open_questions) if mem.open_questions else None,
            json.dumps(mem.code_references) if mem.code_references else None,
            json.dumps(mem.file_references) if mem.file_references else None,
            json.dumps(mem.tools_used) if mem.tools_used else None,
            json.dumps([e.model_dump() for e in mem.errors_found]) if mem.errors_found else None,
            json.dumps(mem.lessons_learned) if mem.lessons_learned else None,
            mem.importance_score,
            mem.recency_score,
            mem.confidence_score,
            mem.stability,
            mem.validity,
            mem.evidence_strength,
            json.dumps(mem.contradiction_links) if mem.contradiction_links else None,
            json.dumps(mem.dependency_links) if mem.dependency_links else None,
            mem.parent_memory_id,
            json.dumps(mem.child_memory_ids) if mem.child_memory_ids else None,
            json.dumps(mem.graph_node_ids) if mem.graph_node_ids else None,
            json.dumps(mem.embedding_vector) if mem.embedding_vector else None,
            mem.embedding_model,
            mem.access_scope,
            int(mem.cross_session),
            int(mem.cross_project),
            mem.ttl_days,
            mem.decay_policy,
            int(mem.never_delete),
            mem.version,
            mem.schema_version,
            json.dumps(mem.audit_log) if mem.audit_log else None,
        )

    def _row_to_memory(self, row: sqlite3.Row) -> MemoryObject:
        def _load_json(val: Optional[str], default: Any = None):
            return json.loads(val) if val else default
        return MemoryObject(
            memory_id=row["memory_id"],
            project_id=row["project_id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            memory_type=row["memory_type"],
            source_type=row["source_type"],
            source_pointer=SourcePointer(**json.loads(row["source_pointer"])) if row["source_pointer"] else None,
            raw_text=row["raw_text"],
            compressed_summary=row["compressed_summary"],
            semantic_summary=row["semantic_summary"],
            entities=[EntityRef(**e) for e in _load_json(row["entities"], [])],
            intents=_load_json(row["intents"], []),
            decisions=[DecisionEntry(**d) for d in _load_json(row["decisions"], [])],
            constraints=_load_json(row["constraints"], []),
            assumptions=_load_json(row["assumptions"], []),
            open_questions=_load_json(row["open_questions"], []),
            code_references=_load_json(row["code_references"], []),
            file_references=_load_json(row["file_references"], []),
            tools_used=_load_json(row["tools_used"], []),
            errors_found=[ErrorEntry(**e) for e in _load_json(row["errors_found"], [])],
            lessons_learned=_load_json(row["lessons_learned"], []),
            importance_score=row["importance_score"],
            recency_score=row["recency_score"],
            confidence_score=row["confidence_score"],
            stability=row["stability"],
            validity=row["validity"],
            evidence_strength=row["evidence_strength"],
            contradiction_links=_load_json(row["contradiction_links"], []),
            dependency_links=_load_json(row["dependency_links"], []),
            parent_memory_id=row["parent_memory_id"],
            child_memory_ids=_load_json(row["child_memory_ids"], []),
            graph_node_ids=_load_json(row["graph_node_ids"], []),
            embedding_vector=json.loads(row["embedding_vector"]) if row["embedding_vector"] else None,
            embedding_model=row["embedding_model"],
            access_scope=row["access_scope"],
            cross_session=bool(row["cross_session"]),
            cross_project=bool(row["cross_project"]),
            ttl_days=row["ttl_days"],
            decay_policy=row["decay_policy"],
            never_delete=bool(row["never_delete"]),
            version=row["version"],
            schema_version=row["schema_version"],
            audit_log=_load_json(row["audit_log"], []),
        )