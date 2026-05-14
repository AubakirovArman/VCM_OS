"""Memory health dashboard — compute metrics and diagnostics for the memory store."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from vcm_os.schemas import MemoryObject, Validity


class MemoryHealthDashboard:
    """Compute health metrics from a SQLiteStore."""

    def __init__(self, store, cache_ttl_seconds: int = 60):
        self.store = store
        self._cache_ttl = cache_ttl_seconds
        self._cached_snapshot: Optional[Dict[str, Any]] = None
        self._cached_at: Optional[datetime] = None

    def snapshot(self) -> Dict[str, Any]:
        """Return a full health snapshot (cached for incremental updates)."""
        now = datetime.now(timezone.utc)
        if self._cached_snapshot and self._cached_at:
            elapsed = (now - self._cached_at).total_seconds()
            if elapsed < self._cache_ttl:
                self._cached_snapshot["cached"] = True
                self._cached_snapshot["cache_age_seconds"] = round(elapsed, 1)
                return self._cached_snapshot

        basic = self._basic_counts()
        validity = self._validity_distribution()
        ages = self._memory_ages()
        orphans = self._orphaned_memories()
        recent = self._recent_activity()
        projects = self._project_health()
        duplicates = self._duplicate_detection()
        decisions = self._decision_breakdown()
        errors = self._error_trends()
        result = {
            "basic": basic,
            "validity": validity,
            "ages": ages,
            "orphans": orphans,
            "recent_activity": recent,
            "projects": projects,
            "duplicates": duplicates,
            "decisions": decisions,
            "errors": errors,
            "score": self._overall_score(basic, validity, orphans, duplicates),
            "cached": False,
            "cache_age_seconds": 0,
        }
        self._cached_snapshot = result
        self._cached_at = now
        return result

    def _basic_counts(self) -> Dict[str, int]:
        stats = self.store.get_stats()
        return {
            "events": stats.get("events", 0),
            "memories": stats.get("memories", 0),
            "projects": stats.get("projects", 0),
            "sessions": stats.get("sessions", 0),
            "db_size_bytes": stats.get("db_size_bytes", 0),
            "memory_types": stats.get("memory_types", {}),
        }

    def _validity_distribution(self) -> Dict[str, int]:
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT validity, COUNT(*) FROM memory_objects GROUP BY validity"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def _memory_ages(self) -> Dict[str, Any]:
        with self.store._conn() as conn:
            row = conn.execute(
                "SELECT AVG(julianday('now') - julianday(timestamp)), "
                "MAX(julianday('now') - julianday(timestamp)), "
                "MIN(julianday('now') - julianday(timestamp)) "
                "FROM memory_objects"
            ).fetchone()
        avg_age = round(row[0] or 0, 2) if row[0] else 0
        max_age = round(row[1] or 0, 2) if row[1] else 0
        min_age = round(row[2] or 0, 2) if row[2] else 0
        return {"avg_days": avg_age, "max_days": max_age, "min_days": min_age}

    def _orphaned_memories(self) -> Dict[str, Any]:
        with self.store._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM memory_objects").fetchone()[0]
            linked = conn.execute(
                "SELECT COUNT(DISTINCT source_id) FROM memory_links "
                "UNION SELECT COUNT(DISTINCT target_id) FROM memory_links"
            ).fetchall()
            linked_ids = set()
            for r in linked:
                if r[0]:
                    linked_ids.add(r[0])
            orphan_count = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE memory_id NOT IN "
                "(SELECT source_id FROM memory_links UNION SELECT target_id FROM memory_links)"
            ).fetchone()[0]
        ratio = orphan_count / total if total > 0 else 0
        return {"count": orphan_count, "ratio": round(ratio, 3), "total": total}

    def _recent_activity(self) -> Dict[str, int]:
        with self.store._conn() as conn:
            d24 = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-1 day')"
            ).fetchone()[0]
            d7 = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-7 day')"
            ).fetchone()[0]
            d30 = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-30 day')"
            ).fetchone()[0]
        return {"last_24h": d24, "last_7d": d7, "last_30d": d30}

    def _project_health(self) -> List[Dict[str, Any]]:
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT project_id, COUNT(*) as cnt FROM memory_objects GROUP BY project_id ORDER BY cnt DESC LIMIT 20"
            ).fetchall()
        return [{"project_id": r[0], "memory_count": r[1]} for r in rows]

    def _duplicate_detection(self) -> Dict[str, Any]:
        with self.store._conn() as conn:
            rows = conn.execute(
                "SELECT content_hash, COUNT(*) FROM canonical_hashes GROUP BY content_hash HAVING COUNT(*) > 1"
            ).fetchall()
        duplicate_groups = len(rows)
        duplicate_memories = sum(r[1] for r in rows)
        return {
            "duplicate_groups": duplicate_groups,
            "duplicate_memories": duplicate_memories,
            "has_duplicates": duplicate_groups > 0,
        }

    def _decision_breakdown(self) -> Dict[str, int]:
        with self.store._conn() as conn:
            # decision memories by validity
            rows = conn.execute(
                "SELECT validity, COUNT(*) FROM memory_objects WHERE memory_type = 'decision' GROUP BY validity"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def _error_trends(self) -> Dict[str, Any]:
        with self.store._conn() as conn:
            total_errors = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE memory_type = 'error'"
            ).fetchone()[0]
            recent_errors = conn.execute(
                "SELECT COUNT(*) FROM memory_objects WHERE memory_type = 'error' AND timestamp > datetime('now', '-7 day')"
            ).fetchone()[0]
        return {"total_errors": total_errors, "recent_7d": recent_errors}

    def _overall_score(self, basic, validity, orphans, duplicates) -> float:
        """Compute an overall health score 0-1."""
        score = 1.0
        # Penalize high orphan ratio
        if orphans["ratio"] > 0.5:
            score -= 0.2
        elif orphans["ratio"] > 0.2:
            score -= 0.1
        # Penalize duplicates
        if duplicates["has_duplicates"]:
            score -= 0.1
        # Penalize stale ratio
        total = basic["memories"]
        stale = validity.get("stale", 0) + validity.get("superseded", 0) + validity.get("archived", 0)
        if total > 0 and stale / total > 0.3:
            score -= 0.1
        return max(0.0, round(score, 2))
