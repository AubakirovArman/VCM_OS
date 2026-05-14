from typing import List, Optional

from vcm_os.schemas import ContextPack, MemoryObject, MemoryRequest, SessionCheckpoint, SessionIdentity, SessionState


class PackAssemblerMixin:
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
        allocation = self.budget_manager.allocate(request.task_type, request.token_budget)
        pack, warnings = self._init_pack(request, active_state, session)
        # Filter out stale/superseded/rejected memories before packing
        active_candidates = [m for m in candidates if m.validity not in ("stale", "superseded", "rejected")]
        buckets = self._categorize(active_candidates)

        stale_count = sum(1 for m in candidates if m.validity in ("stale", "superseded", "rejected"))
        if stale_count:
            warnings.append(f"Filtered {stale_count} stale/superseded/rejected memories from pack.")

        # Project State Object slot (v0.7)
        if project_state_text:
            from vcm_os.schemas import ContextPackSection
            pso_section = ContextPackSection(
                section_name="project_state",
                content=project_state_text,
                token_estimate=len(project_state_text.split()),
            )
            pack.sections.insert(0, pso_section)

        # Exact Symbol Vault slot (v0.8)
        if symbol_vault_text:
            from vcm_os.schemas import ContextPackSection
            sv_section = ContextPackSection(
                section_name="exact_symbols",
                content=symbol_vault_text,
                token_estimate=len(symbol_vault_text.split()),
            )
            pack.sections.insert(0, sv_section)

        # Superseded warnings removed — stale/superseded already filtered above

        seen_ids = set()
        seen_raw_text = set()

        if request.task_type == "debugging":
            pack.sections.append(self._build_section("errors", buckets["errors"], allocation["errors"], 3, seen_ids, seen_raw_text, max_items=2, request=request))
            pack.sections.append(self._build_section("decisions", buckets["decisions"], allocation["decisions"], 3, seen_ids, seen_raw_text, max_items=2, request=request))
            pack.sections.append(self._build_section("code_context", buckets["code"], allocation["code_context"], 4, seen_ids, seen_raw_text, max_items=1, request=request))
        elif request.task_type == "architecture":
            pack.sections.append(self._build_section("decisions", buckets["decisions"], allocation["decisions"], 3, seen_ids, seen_raw_text, max_items=2, request=request))
            pack.sections.append(self._build_section("requirements", buckets["requirements"], allocation["requirements"], 4, seen_ids, seen_raw_text, max_items=1, request=request))
        else:
            pack.sections.append(self._build_section("decisions", buckets["decisions"], allocation["decisions"], 3, seen_ids, seen_raw_text, max_items=2, request=request))
            pack.sections.append(self._build_section("errors", buckets["errors"], allocation["errors"], 3, seen_ids, seen_raw_text, max_items=2, request=request))
            q_lower = request.query.lower()
            if any(k in q_lower for k in ["debug", "fix", "error", "bug", "crash", "test fail", "broken"]):
                pack.sections.append(self._build_section("code_context", buckets["code"], allocation["code_context"], 4, seen_ids, seen_raw_text, max_items=1, request=request))
            elif buckets["code"]:
                pack.sections.append(self._build_section("code_context", buckets["code"], allocation.get("code_context", 20), 4, seen_ids, seen_raw_text, max_items=1, request=request))

        # Goals section (v0.9) — helps verbatim goal recall
        # v0.10: compact filler sections
        filler_budget = 12
        if buckets["goals"]:
            pack.sections.append(self._build_section("goals", buckets["goals"], 20, 3, seen_ids, seen_raw_text, max_items=1, request=request))
        if buckets["requirements"]:
            req_budget = min(allocation.get("requirements", 20), 14)
            pack.sections.append(self._build_section("requirements", buckets["requirements"], req_budget, 4, seen_ids, seen_raw_text, max_items=1, request=request))
        if buckets["intents"]:
            pack.sections.append(self._build_section("intents", buckets["intents"], filler_budget, 4, seen_ids, seen_raw_text, max_items=1, request=request))
        if buckets["reflections"]:
            pack.sections.append(self._build_section("reflections", buckets["reflections"], filler_budget, 4, seen_ids, seen_raw_text, max_items=1, request=request))
        if buckets["uncertainties"] or buckets["tasks"]:
            pack.sections.append(self._build_section("open_questions", buckets["uncertainties"] + buckets["tasks"], filler_budget, 4, seen_ids, seen_raw_text, max_items=1, request=request))

        pack, seen_ids, rescue_warning = self._run_rescue(pack, candidates, seen_ids, request)
        if rescue_warning:
            warnings.append(rescue_warning)

        pack.forbidden_context = [f"Scope:{request.project_id}"]
        pack.token_estimate = sum(s.token_estimate for s in pack.sections)

        # Hard token cap enforcement (v0.8): trim non-critical sections if over budget
        hard_cap = min(request.token_budget, request.max_pack_tokens)
        while pack.token_estimate > hard_cap and len(pack.sections) > 3:
            trimmable = [s for s in pack.sections if s.section_name in (
                "intents", "reflections", "procedures", "facts", "open_questions"
            )]
            if trimmable:
                victim = trimmable[-1]
                pack.token_estimate -= victim.token_estimate
                pack.sections.remove(victim)
                warnings.append(f"Trimmed {victim.section_name} to stay under {hard_cap} tokens.")
            else:
                break

        has_decisions = any(s.section_name == "decisions" and s.memory_ids for s in pack.sections)
        has_errors = any(s.section_name == "errors" and s.memory_ids for s in pack.sections)
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
