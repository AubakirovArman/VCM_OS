from typing import Any, Dict

from vcm_os.llm_client import LLMClient
from vcm_os.schemas import ContextPack


class SufficiencyChecker:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def check(
        self,
        query: str,
        pack: ContextPack,
    ) -> Dict[str, Any]:
        pack_text = "\n\n".join(
            f"[{s.section_name}]\n{s.content}" for s in pack.sections if s.content.strip()
        )
        result = await self.llm.check_sufficiency(query, pack_text)
        # Update pack score
        pack.sufficiency_score = result.get("score", 0.5)
        return result

    def check_heuristic(self, query: str, pack: ContextPack) -> Dict[str, Any]:
        # Non-LLM fallback: check if key query terms appear in pack
        query_terms = set(query.lower().split())
        pack_text = " ".join(s.content.lower() for s in pack.sections)
        found = sum(1 for term in query_terms if term in pack_text)
        coverage = found / max(len(query_terms), 1)
        score = min(1.0, coverage * 1.5)
        sufficient = score > 0.5
        missing = []
        if not sufficient:
            missing = [term for term in query_terms if term not in pack_text][:5]
        return {"sufficient": sufficient, "score": score, "missing": missing}
