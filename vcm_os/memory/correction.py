"""Human-in-the-loop memory correction service."""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from vcm_os.schemas import MemoryObject, Validity


class MemoryCorrection:
    """A single correction action on a memory."""

    def __init__(
        self,
        memory_id: str,
        action: str,  # stale, incorrect, important, duplicate, pin, delete
        reason: str = "",
        user_id: str = "",
        timestamp: Optional[str] = None,
    ):
        self.memory_id = memory_id
        self.action = action
        self.reason = reason
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()


class CorrectionService:
    """Service for applying corrections to memories and tracking them."""

    VALID_ACTIONS = {"stale", "incorrect", "important", "duplicate", "pin", "unpin", "delete"}

    def __init__(self, store):
        self.store = store

    def apply(self, correction: MemoryCorrection) -> Dict:
        """Apply a correction to a memory."""
        if correction.action not in self.VALID_ACTIONS:
            return {"success": False, "error": f"Invalid action: {correction.action}"}

        mem = self.store.get_memory(correction.memory_id)
        if not mem:
            return {"success": False, "error": "Memory not found"}

        result = {"memory_id": correction.memory_id, "action": correction.action}

        if correction.action == "stale":
            mem.validity = Validity.SUPERSEDED
            self.store.update_memory(mem)
            result["new_validity"] = "superseded"

        elif correction.action == "incorrect":
            mem.validity = Validity.DISPUTED
            self.store.update_memory(mem)
            result["new_validity"] = "disputed"

        elif correction.action == "important":
            mem.importance_score = min(1.0, (mem.importance_score or 0.5) + 0.2)
            mem.never_delete = True
            self.store.update_memory(mem)
            result["new_importance"] = mem.importance_score

        elif correction.action == "duplicate":
            # Mark as archived, link to canonical
            mem.validity = Validity.ARCHIVED
            self.store.update_memory(mem)
            result["new_validity"] = "archived"

        elif correction.action == "pin":
            mem.never_delete = True
            self.store.update_memory(mem)
            result["pinned"] = True

        elif correction.action == "unpin":
            mem.never_delete = False
            self.store.update_memory(mem)
            result["pinned"] = False

        elif correction.action == "delete":
            self.store.delete_memory(correction.memory_id)
            result["deleted"] = True

        # Store correction log
        self._log_correction(correction)
        result["success"] = True
        return result

    def batch_apply(self, corrections: List[MemoryCorrection]) -> List[Dict]:
        """Apply multiple corrections."""
        return [self.apply(c) for c in corrections]

    def get_correction_history(self, memory_id: str) -> List[Dict]:
        """Get correction history for a memory."""
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT action, reason, user_id, timestamp FROM memory_corrections WHERE memory_id = ? ORDER BY timestamp DESC",
                (memory_id,),
            ).fetchall()
        return [
            {"action": r[0], "reason": r[1], "user_id": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def get_review_queue(self, project_id: str, limit: int = 20) -> List[MemoryObject]:
        """Get low-confidence memories needing review."""
        mems = self.store.get_memories(project_id=project_id, limit=200)
        # Filter: low confidence, no corrections yet, not already reviewed
        queue = []
        for m in mems:
            if m.confidence_score and m.confidence_score < 0.5:
                history = self.get_correction_history(m.memory_id)
                if not history:
                    queue.append(m)
            if len(queue) >= limit:
                break
        return queue

    def _log_correction(self, correction: MemoryCorrection) -> None:
        """Store correction in audit log."""
        with self.store._conn() as conn:
            conn.execute(
                """INSERT INTO memory_corrections (memory_id, action, reason, user_id, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (correction.memory_id, correction.action, correction.reason, correction.user_id, correction.timestamp),
            )

    def get_correction_stats(self, project_id: str) -> Dict:
        """Get correction statistics for a project."""
        with self.store._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memory_corrections WHERE memory_id IN (SELECT memory_id FROM memory_objects WHERE project_id = ?)",
                (project_id,),
            ).fetchone()[0]
            action_counts = conn.execute(
                "SELECT action, COUNT(*) FROM memory_corrections WHERE memory_id IN (SELECT memory_id FROM memory_objects WHERE project_id = ?) GROUP BY action",
                (project_id,),
            ).fetchall()
        return {
            "total_corrections": total,
            "by_action": {r[0]: r[1] for r in action_counts},
        }
