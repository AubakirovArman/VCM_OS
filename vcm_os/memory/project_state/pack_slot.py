"""Project State Object pack slot for context builder v2."""
from typing import Optional

from vcm_os.memory.project_state.schema import ProjectStateObject
from vcm_os.memory.project_state.store import ProjectStateStore


class ProjectStateSlot:
    """Provide PSO as a first-class context pack slot."""

    def __init__(self, store: ProjectStateStore):
        self.store = store

    def get_slot_text(self, project_id: str, max_items: int = 1, stale_terms: list = None) -> str:
        """Render PSO as structured text for inclusion in a context pack.
        Filters out items that match stale_terms."""
        pso = self.store.load(project_id)
        if not pso:
            return ""

        stale_lower = [s.lower() for s in (stale_terms or [])]

        def _is_stale(text: str) -> bool:
            t = text.lower()
            return any(s in t for s in stale_lower)

        def _trunc(text: str, limit: int = 40) -> str:
            return text if len(text) <= limit else text[:limit - 3] + "..."

        parts = []

        # Phase + milestone + branch (compact header)
        header_parts = []
        if pso.project_phase:
            header_parts.append(f"ph={pso.project_phase}")
        if pso.current_milestone:
            header_parts.append(f"ms={_trunc(pso.current_milestone, 30)}")
        if pso.current_branch:
            header_parts.append(f"br={pso.current_branch}")
        if header_parts:
            parts.append(" ".join(header_parts))

        # Status
        status_parts = []
        if pso.test_status:
            status_parts.append(f"t={pso.test_status}")
        if pso.deployment_status:
            status_parts.append(f"dpl={pso.deployment_status}")
        if status_parts:
            parts.append(" ".join(status_parts))

        # Core items
        if pso.active_goals:
            goals = [g for g in pso.active_goals if not _is_stale(g)][:max_items]
            for g in goals:
                parts.append(f"g={_trunc(g, 40)}")
        if pso.open_tasks:
            tasks = [t for t in pso.open_tasks if not _is_stale(t)][:max_items]
            for t in tasks:
                parts.append(f"t={_trunc(t, 40)}")
        if pso.blocked_tasks:
            blocked = [b for b in pso.blocked_tasks if not _is_stale(b)][:max_items]
            for b in blocked:
                parts.append(f"blk={_trunc(b, 40)}")
        if pso.latest_decisions:
            decs = [d for d in pso.latest_decisions if not _is_stale(d)][:max_items]
            for d in decs:
                parts.append(f"d={_trunc(d, 40)}")
        if pso.current_bugs:
            bugs = [b for b in pso.current_bugs if not _is_stale(b)][:max_items]
            for b in bugs:
                parts.append(f"b={_trunc(b, 40)}")
        if pso.recently_changed_files:
            files = pso.recently_changed_files[:2]
            parts.append(f"f={','.join(files)}")
        if pso.active_experiments:
            exps = pso.active_experiments[:1]
            for e in exps:
                parts.append(f"exp={_trunc(e, 40)}")
        if pso.risk_register:
            risks = pso.risk_register[:1]
            for r in risks:
                parts.append(f"risk={_trunc(r, 40)}")
        if pso.constraints:
            cons = [c for c in pso.constraints if not _is_stale(c)][:max_items]
            for c in cons:
                parts.append(f"c={_trunc(c, 40)}")

        return " ".join(parts) if parts else "### Project State"
