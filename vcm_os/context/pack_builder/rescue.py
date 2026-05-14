from typing import Dict, List, Set

from vcm_os.schemas import ContextPack, ContextPackSection, MemoryObject, MemoryRequest
from vcm_os.context.keyword_extractor import extract_protected_keywords


class RescueMixin:
    def _run_rescue(
        self,
        pack: ContextPack,
        candidates: List[MemoryObject],
        seen_ids: Set[str],
        request: MemoryRequest,
    ) -> tuple:
        pack_text = " ".join(s.content.lower() for s in pack.sections)
        missing_terms = set()
        candidate_term_map: Dict[str, MemoryObject] = {}

        for term in request.required_terms:
            t_lower = term.lower()
            if t_lower not in pack_text:
                missing_terms.add(t_lower)

        for m in candidates:
            if m.memory_id in seen_ids:
                continue
            terms = extract_protected_keywords(m.raw_text or "")
            for t in terms:
                t_lower = t.lower()
                if t_lower not in pack_text:
                    missing_terms.add(t_lower)
                    if t_lower not in candidate_term_map or (
                        m.importance_score > candidate_term_map[t_lower].importance_score
                    ):
                        candidate_term_map[t_lower] = m

        for term in request.required_terms:
            t_lower = term.lower()
            if t_lower in missing_terms and t_lower not in candidate_term_map:
                for m in candidates:
                    if m.memory_id in seen_ids:
                        continue
                    if t_lower in (m.raw_text or "").lower():
                        candidate_term_map[t_lower] = m
                        break

        rescued = []
        rescued_ids = set()
        rescue_budget = 22
        used = 0
        for term in sorted(missing_terms):
            m = candidate_term_map.get(term)
            if not m or m.memory_id in rescued_ids:
                continue
            compressed = self.compressor.compress(m, level=4)
            est = self.budget_manager.estimate_tokens(compressed)
            if used + est > rescue_budget:
                break
            rescued.append(compressed)
            rescued_ids.add(m.memory_id)
            seen_ids.add(m.memory_id)
            used += est

        warning = None
        if rescued:
            pack.sections.append(ContextPackSection(
                section_name="protected_evidence",
                content="\n".join(rescued),
                memory_ids=list(rescued_ids),
                token_estimate=used,
            ))
            warning = f"Rescued {len(rescued)} memories for protected terms."

        return pack, seen_ids, warning
