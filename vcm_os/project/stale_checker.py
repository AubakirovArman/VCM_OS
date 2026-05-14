import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from vcm_os.schemas import MemoryObject
from vcm_os.storage.sqlite_store import SQLiteStore


class StaleChecker:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def check_code_references(self, project_id: str, workspace_root: str) -> List[Dict[str, str]]:
        """Returns list of stale memory entries with outdated file references."""
        stale = []
        code_mems = self.store.get_memories(project_id=project_id, memory_type="code_change", limit=500)
        for mem in code_mems:
            for fpath in mem.file_references:
                full = os.path.join(workspace_root, fpath)
                if not os.path.exists(full):
                    stale.append({
                        "memory_id": mem.memory_id,
                        "file_path": fpath,
                        "reason": "file_not_found",
                    })
        return stale

    def check_decision_consistency(
        self,
        project_id: str,
    ) -> List[Dict[str, str]]:
        """Find active decisions that may be stale due to newer code changes."""
        stale = []
        decisions = self.store.get_memories(
            project_id=project_id,
            memory_type="decision",
            validity="active",
            limit=200,
        )
        for dec in decisions:
            # If decision is older than 30 days and no recent code changes reference it
            # mark as potentially stale
            from datetime import datetime, timezone
            age_days = (datetime.now(timezone.utc) - dec.timestamp).days
            if age_days > 30:
                stale.append({
                    "memory_id": dec.memory_id,
                    "reason": "old_decision_no_recent_activity",
                    "age_days": str(age_days),
                })
        return stale

    def flag_stale_memories(self, project_id: str, workspace_root: Optional[str] = None) -> Dict[str, List[Dict]]:
        result: Dict[str, List[Dict]] = {"code": [], "decisions": []}
        if workspace_root:
            result["code"] = self.check_code_references(project_id, workspace_root)
        result["decisions"] = self.check_decision_consistency(project_id)
        return result
