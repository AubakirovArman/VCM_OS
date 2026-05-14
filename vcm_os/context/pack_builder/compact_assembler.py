"""Compact pack assembler v0.10.1 — minimize tokens by merging sections.

Strategy: reduce section count (3-4 sections vs 10+) while preserving
original compressed content for verbatim matching. No fluff stripping.
"""

from typing import List, Optional, Set

from vcm_os.schemas import ContextPack, ContextPackSection, MemoryObject, MemoryRequest, SessionCheckpoint, SessionIdentity, SessionState
from vcm_os.context.pack_builder.helpers import raw_hash, sort_key


class CompactPackAssemblerMixin:
    """Drop-in replacement for PackAssemblerMixin."""

    def build(
        self,
        request: MemoryRequest,
        candidates: List[MemoryObject],
        checkpoint: Optional[SessionCheckpoint] = None,
        active_state: Optional[SessionState] = None,
        session: Optional[SessionIdentity] = None,
        project_state_text: Optional[str] = None,
        symbol_vault_text: Optional[str] = None,
    ) -> ContextPack:
        pack = ContextPack(project_id=request.project_id, session_id=request.session_id)
        warnings = []

        # --- Meta section (always first, ultra-compact) ---
        meta_parts = []
        q = request.query[:20] if len(request.query) > 20 else request.query
        meta_parts.append(f"p={request.project_id} q={q}")

        if session and session.branch:
            meta_parts.append(f"b={session.branch}")
        if active_state:
            if active_state.active_files:
                meta_parts.append(f"f={','.join(active_state.active_files[:3])}")
            if active_state.open_tasks:
                meta_parts.append(f"t={','.join(active_state.open_tasks[:3])}")

        meta_text = " ".join(meta_parts)
        if meta_text:
            pack.sections.append(ContextPackSection(
                section_name="meta",
                content=meta_text,
                token_estimate=self.budget_manager.estimate_tokens(meta_text),
            ))

        # --- Project State & Symbol Vault (keep full text) ---
        if project_state_text:
            pack.sections.append(ContextPackSection(
                section_name="project_state",
                content=project_state_text,
                token_estimate=self.budget_manager.estimate_tokens(project_state_text),
            ))

        if symbol_vault_text:
            pack.sections.append(ContextPackSection(
                section_name="exact_symbols",
                content=symbol_vault_text,
                token_estimate=self.budget_manager.estimate_tokens(symbol_vault_text),
            ))

        # --- Filter stale/superseded ---
        active_candidates = [m for m in candidates if m.validity not in ("stale", "superseded", "rejected")]
        stale_count = len(candidates) - len(active_candidates)
        if stale_count:
            warnings.append(f"Filtered {stale_count} stale memories.")

        # --- Bucket candidates ---
        buckets = {
            "decisions": [], "errors": [], "code": [],
            "requirements": [], "uncertainties": [], "tasks": [],
            "procedures": [], "reflections": [], "intents": [], "facts": [],
            "goals": [],
        }
        for m in active_candidates:
            t = m.memory_type
            if t == "decision":
                buckets["decisions"].append(m)
            elif t == "error":
                buckets["errors"].append(m)
            elif t == "code_change":
                buckets["code"].append(m)
            elif t == "requirement":
                buckets["requirements"].append(m)
            elif t == "uncertainty":
                buckets["uncertainties"].append(m)
            elif t == "task":
                buckets["tasks"].append(m)
            elif t == "procedure":
                buckets["procedures"].append(m)
            elif t == "reflection":
                buckets["reflections"].append(m)
            elif t == "intent":
                buckets["intents"].append(m)
            elif t == "goal":
                buckets["goals"].append(m)
            elif t in ("fact", "event"):
                buckets["facts"].append(m)

        for k in ("decisions", "errors", "intents", "requirements", "goals"):
            buckets[k].sort(key=sort_key, reverse=True)

        seen_ids: Set[str] = set()
        seen_raw: Set[str] = set()

        # --- Build compact sections (preserve original compressed content) ---

        # State section: decisions + errors + goals
        state_items, state_ids = self._build_compact_items(
            buckets["decisions"] + buckets["errors"] + buckets["goals"],
            seen_ids, seen_raw,
            budget=40, compression_level=2, max_items=6,
        )
        if state_items:
            state_text = "\n".join(state_items)
            pack.sections.append(ContextPackSection(
                section_name="state",
                content=state_text,
                memory_ids=state_ids,
                token_estimate=self.budget_manager.estimate_tokens(state_text),
            ))

        # Context section: requirements + intents + facts + reflections + procedures + uncertainties + tasks
        ctx_mems = (
            buckets["requirements"] + buckets["intents"] + buckets["facts"] +
            buckets["reflections"] + buckets["procedures"] + buckets["uncertainties"] + buckets["tasks"]
        )
        ctx_items, ctx_ids = self._build_compact_items(
            ctx_mems, seen_ids, seen_raw,
            budget=25, compression_level=3, max_items=4,
        )
        if ctx_items:
            ctx_text = "\n".join(ctx_items)
            pack.sections.append(ContextPackSection(
                section_name="context",
                content=ctx_text,
                memory_ids=ctx_ids,
                token_estimate=self.budget_manager.estimate_tokens(ctx_text),
            ))

        # Code section (task-aware)
        max_code = 2 if request.task_type == "debugging" else 1
        code_items, code_ids = self._build_compact_items(
            buckets["code"], seen_ids, seen_raw,
            budget=20, compression_level=2, max_items=max_code,
        )
        if code_items:
            code_text = "\n".join(code_items)
            pack.sections.append(ContextPackSection(
                section_name="code",
                content=code_text,
                memory_ids=code_ids,
                token_estimate=self.budget_manager.estimate_tokens(code_text),
            ))

        # --- Rescue exact symbols ---
        pack, seen_ids, rescue_warning = self._run_rescue(pack, candidates, seen_ids, request)
        if rescue_warning:
            warnings.append(rescue_warning)

        pack.forbidden_context = [f"Scope:{request.project_id}"]
        pack.token_estimate = sum(s.token_estimate for s in pack.sections)

        # Hard cap: trim context/code before state
        hard_cap = min(request.token_budget, request.max_pack_tokens)
        while pack.token_estimate > hard_cap and len(pack.sections) > 3:
            trimmable = [s for s in pack.sections if s.section_name in ("context", "code")]
            if trimmable:
                victim = trimmable[-1]
                pack.token_estimate -= victim.token_estimate
                pack.sections.remove(victim)
                warnings.append(f"Trimmed {victim.section_name} to stay under {hard_cap}.")
            else:
                break

        # Sufficiency score
        has_decisions = any(
            s.section_name == "state" and s.content and "[DECISION]" in s.content
            for s in pack.sections
        )
        has_errors = any(
            s.section_name == "state" and s.content and "[ERROR]" in s.content
            for s in pack.sections
        )
        sufficiency = 0.3
        if has_decisions:
            sufficiency += 0.3
        if has_errors:
            sufficiency += 0.2
        if len(candidates) > 5:
            sufficiency += 0.1
        if len(candidates) > 10:
            sufficiency += 0.1
        pack.sufficiency_score = min(1.0, sufficiency)
        pack.warnings = warnings
        return pack

    def _build_compact_items(
        self,
        mems: List[MemoryObject],
        seen_ids: Set[str],
        seen_raw: Set[str],
        budget: int,
        compression_level: int,
        max_items: Optional[int] = None,
    ) -> tuple:
        items = []
        ids = []
        used = 0
        count = 0
        for m in mems:
            if m.memory_id in seen_ids:
                continue
            h = raw_hash(m)
            if h and h in seen_raw:
                continue
            if h:
                seen_raw.add(h)

            compressed = self.compressor.compress(m, level=compression_level)
            if len(compressed) > 80:
                compressed = compressed[:80]
            est = self.budget_manager.estimate_tokens(compressed)
            if used + est > budget:
                break
            items.append(compressed)
            ids.append(m.memory_id)
            seen_ids.add(m.memory_id)
            used += est
            count += 1
            if max_items and count >= max_items:
                break
        return items, ids
