"""Auto-expand insufficient context packs by rewriting queries and re-retrieving."""
from typing import Dict, List, Optional

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.verifier.pack_sufficiency import PackSufficiencyVerifier
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.schemas import ContextPack, MemoryObject, MemoryRequest


class PackAutoExpander:
    """Automatically expand a pack when it's insufficient for the query."""

    def __init__(self, reader: MemoryReader, router: MemoryRouter, scorer: MemoryScorer, pack_builder: ContextPackBuilder):
        self.reader = reader
        self.router = router
        self.scorer = scorer
        self.pack_builder = pack_builder
        self.sufficiency = PackSufficiencyVerifier()

    def build_with_fallback(self, request: MemoryRequest, max_expansions: int = 2) -> ContextPack:
        """Build a pack, auto-expanding if insufficient."""
        plan = self.router.make_plan(request)
        candidates = self.reader.retrieve(request, plan)
        scored = self.scorer.rerank(candidates, request)
        memories = [m for m, _ in scored[:50]]

        pack = self.pack_builder.build(request, memories)
        suff = self.sufficiency.verify(request.query, pack, memories)

        for i in range(max_expansions):
            if suff["sufficient"]:
                break

            # Rewrite query based on issues
            new_query = self._rewrite_query(request.query, suff["issues"])
            if new_query == request.query:
                break

            request = MemoryRequest(
                project_id=request.project_id,
                session_id=request.session_id,
                query=new_query,
                task_type=request.task_type,
                token_budget=request.token_budget,
                required_terms=request.required_terms,
            )

            plan = self.router.make_plan(request)
            candidates = self.reader.retrieve(request, plan)
            scored = self.scorer.rerank(candidates, request)
            new_memories = [m for m, _ in scored[:50]]

            # Merge memories, avoiding duplicates
            seen_ids = {m.memory_id for m in memories}
            for m in new_memories:
                if m.memory_id not in seen_ids:
                    memories.append(m)

            pack = self.pack_builder.build(request, memories)
            suff = self.sufficiency.verify(request.query, pack, memories)

        pack.sufficiency_score = suff.get("score", 1.0)
        return pack

    def _rewrite_query(self, query: str, issues: List[Dict]) -> str:
        """Rewrite query based on sufficiency issues."""
        rewritten = query

        for issue in issues:
            itype = issue.get("type")

            if itype == "keyword_gap" and issue.get("missing"):
                # Add missing keywords to query
                missing = issue["missing"]
                rewritten += " " + " ".join(missing[:3])

            elif itype == "missing_memory_type":
                # Add memory type hint to query
                required = issue.get("required", "")
                if required and required not in rewritten.lower():
                    rewritten += f" {required}"

            elif itype == "pack_too_short":
                # Broaden query
                if "recent" not in rewritten.lower():
                    rewritten += " recent"

        return rewritten.strip()
