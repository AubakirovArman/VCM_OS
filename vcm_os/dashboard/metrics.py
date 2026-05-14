"""Real-time metrics collection for VCM-OS dashboard."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from vcm_os.health.dashboard import MemoryHealthDashboard


class DashboardMetrics:
    """Collect and format metrics for the production dashboard."""

    def __init__(self, store, vector_index, sparse_index):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.health = MemoryHealthDashboard(store)

    def snapshot(self) -> Dict[str, Any]:
        """Full dashboard snapshot."""
        health = self.health.snapshot()
        latency = self._latency_metrics()
        retrieval = self._retrieval_metrics()
        errors = self._error_metrics()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": health,
            "latency": latency,
            "retrieval": retrieval,
            "errors": errors,
            "version": "0.5.0",
        }

    def _latency_metrics(self) -> Dict[str, Any]:
        """Recent operation latencies."""
        with self.store._conn() as conn:
            # Average event ingestion time if we tracked it
            recent_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-1 hour')"
            ).fetchone()[0]
            recent_memories = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE timestamp > datetime('now', '-1 hour')"
            ).fetchone()[0]
        return {
            "recent_events_1h": recent_events,
            "recent_memories_1h": recent_memories,
            "vector_index_size": len(self.vector_index._ids) if hasattr(self.vector_index, '_ids') else 0,
            "sparse_index_size": len(self.sparse_index._index) if hasattr(self.sparse_index, '_index') else 0,
        }

    def _retrieval_metrics(self) -> Dict[str, Any]:
        """Retrieval quality metrics."""
        with self.store._conn() as conn:
            total_memories = conn.execute("SELECT COUNT(*) FROM memory_objects").fetchone()[0]
            linked_memories = conn.execute(
                "SELECT COUNT(DISTINCT source_id) FROM memory_links"
            ).fetchone()[0]
            by_type = conn.execute(
                "SELECT memory_type, COUNT(*) FROM memory_objects GROUP BY memory_type"
            ).fetchall()
        return {
            "total_memories": total_memories,
            "linked_memories": linked_memories,
            "link_ratio": round(linked_memories / total_memories, 3) if total_memories > 0 else 0,
            "by_type": {r[0]: r[1] for r in by_type},
        }

    def _error_metrics(self) -> Dict[str, Any]:
        """Error and failure metrics."""
        with self.store._conn() as conn:
            recent_errors = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE memory_type = 'error' AND timestamp > datetime('now', '-24 hour')"
            ).fetchone()[0]
            disputed = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE validity = 'disputed'"
            ).fetchone()[0]
            stale = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE validity IN ('stale', 'superseded', 'archived')"
            ).fetchone()[0]
            # Corrections applied
            corrections = conn.execute("SELECT COUNT(*) FROM memory_corrections").fetchone()[0]
        return {
            "recent_errors_24h": recent_errors,
            "disputed_memories": disputed,
            "stale_memories": stale,
            "total_corrections": corrections,
        }
