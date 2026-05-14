from typing import List, Optional

from vcm_os.schemas import (
    ContextPack,
    ContextPackSection,
    MemoryObject,
    MemoryRequest,
    SessionCheckpoint,
    SessionIdentity,
    SessionState,
)
from vcm_os.context.pack_builder.helpers import raw_hash, sort_key
from vcm_os.context.learned_token_budget import LearnedTokenBudgetManager
from vcm_os.memory.compressor import MemoryCompressor


class ContextPackBuilderCore:
    def __init__(self):
        self.budget_manager = LearnedTokenBudgetManager()
        self.compressor = MemoryCompressor()

    def _build_section(
        self,
        name: str,
        mems: List[MemoryObject],
        budget: int,
        compression_level: int,
        seen_ids: set,
        seen_raw_text: set,
        max_items: Optional[int] = None,
        request: Optional[MemoryRequest] = None,
    ) -> ContextPackSection:
        content_parts = []
        ids = []
        used = 0
        count = 0
        # Dynamic scaling based on pack budget
        pack_budget = request.max_pack_tokens if request else 65
        scale = min(5.0, max(1.0, pack_budget / 100))
        effective_max_items = max_items
        if max_items and pack_budget > 150:
            effective_max_items = max_items + int((pack_budget - 150) / 100)
        for m in mems:
            if m.memory_id in seen_ids:
                continue
            h = raw_hash(m)
            if h and h in seen_raw_text:
                continue
            if h:
                seen_raw_text.add(h)

            compressed = self.compressor.compress(m, level=compression_level)
            # Adaptive per-item cap: preserve exact symbols
            from vcm_os.context.keyword_extractor import extract_protected_keywords
            protected = extract_protected_keywords(m.raw_text or "")
            base_cap = 100 if protected else 72
            cap = int(base_cap * scale)
            if len(compressed) > cap:
                compressed = compressed[:cap]
            est = self.budget_manager.estimate_tokens(compressed)
            if used + est > budget:
                break
            content_parts.append(compressed)
            ids.append(m.memory_id)
            seen_ids.add(m.memory_id)
            used += est
            count += 1
            if effective_max_items and count >= effective_max_items:
                break
        return ContextPackSection(
            section_name=name,
            content="\n".join(content_parts),
            memory_ids=ids,
            token_estimate=used,
        )

    def _init_pack(
        self,
        request: MemoryRequest,
        active_state: Optional[SessionState],
        session: Optional[SessionIdentity],
    ) -> tuple:
        pack = ContextPack(project_id=request.project_id, session_id=request.session_id)
        warnings = []

        q = request.query[:20] if len(request.query) > 20 else request.query
        system_text = f"p={request.project_id} q={q}"
        sys_tokens = self.budget_manager.estimate_tokens(system_text)
        pack.sections.append(ContextPackSection(
            section_name="system_task",
            content=system_text,
            token_estimate=sys_tokens,
        ))

        if active_state:
            parts = []
            if session and session.branch:
                parts.append(f"b={session.branch}")
            if active_state.active_files:
                parts.append(f"f={','.join(active_state.active_files[:3])}")
            if active_state.open_tasks:
                parts.append(f"t={','.join(active_state.open_tasks[:3])}")
            sess_text = ";".join(parts) if parts else ""
            if sess_text:
                pack.sections.append(ContextPackSection(
                    section_name="session_state",
                    content=sess_text,
                    token_estimate=self.budget_manager.estimate_tokens(sess_text),
                    memory_ids=active_state.recent_decisions[-3:] + active_state.recent_errors[-3:],
                ))

        return pack, warnings

    def _categorize(self, candidates: List[MemoryObject]) -> dict:
        buckets = {
            "decisions": [], "errors": [], "code": [],
            "requirements": [], "uncertainties": [], "tasks": [],
            "procedures": [], "reflections": [], "intents": [], "facts": [],
            "goals": [],
        }
        for m in candidates:
            t = m.memory_type
            # Handle both enum and string values
            t_val = t.value if hasattr(t, "value") else str(t)
            if t_val == "decision":
                buckets["decisions"].append(m)
            elif t_val == "error":
                buckets["errors"].append(m)
            elif t_val == "code_change":
                buckets["code"].append(m)
            elif t_val == "requirement":
                buckets["requirements"].append(m)
            elif t_val == "uncertainty":
                buckets["uncertainties"].append(m)
            elif t_val == "task":
                buckets["tasks"].append(m)
            elif t_val == "procedure":
                buckets["procedures"].append(m)
            elif t_val == "reflection":
                buckets["reflections"].append(m)
            elif t_val == "intent":
                buckets["intents"].append(m)
            elif t_val == "goal":
                buckets["goals"].append(m)
            elif t_val in ("fact", "event"):
                buckets["facts"].append(m)
        for k in ("decisions", "errors", "intents", "requirements", "goals"):
            buckets[k].sort(key=sort_key, reverse=True)
        return buckets
