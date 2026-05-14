import re
from typing import Dict, List, Optional, Tuple

from vcm_os.llm_client import LLMClient
from vcm_os.schemas import ContextPack, MemoryObject
from vcm_os.storage.sqlite_store import SQLiteStore


class ConsistencyVerifier:
    def __init__(self, store: SQLiteStore, llm: Optional[LLMClient] = None):
        self.store = store
        self.llm = llm

    def verify_answer(
        self,
        query: str,
        answer: str,
        pack: ContextPack,
    ) -> Dict[str, any]:
        """Verify if answer is consistent with retrieved memories."""
        violations = []
        warnings = []
        citations = []

        # 1. Check cited memory IDs exist and are active
        cited_ids = re.findall(r"mem_[a-f0-9]+", answer)
        for mid in cited_ids:
            mem = self.store.get_memory(mid)
            if not mem:
                violations.append(f"Cited memory {mid} does not exist")
            elif mem.validity in ("superseded", "rejected", "archived"):
                violations.append(f"Cited memory {mid} is {mem.validity}")
            else:
                citations.append(mid)

        # 2. Check for contradictions with active decisions
        active_decisions = self.store.get_memories(
            project_id=pack.project_id,
            memory_type="decision",
            validity="active",
            limit=50,
        )
        for dec in active_decisions:
            for d_entry in dec.decisions:
                if self._contradicts(answer, d_entry.statement):
                    violations.append(f"Answer contradicts active decision: {d_entry.statement}")

        # 3. Check for false claims about file changes
        if "changed" in answer.lower() or "modified" in answer.lower():
            if not any("tool" in s.content.lower() for s in pack.sections):
                warnings.append("Answer claims file changes but no tool evidence in pack")

        # 4. Check cross-project contamination
        pack_text = " ".join(s.content for s in pack.sections).lower()
        other_projects = set()
        for mem_id in [m for s in pack.sections for m in s.memory_ids]:
            mem = self.store.get_memory(mem_id)
            if mem and mem.project_id != pack.project_id:
                other_projects.add(mem.project_id)
        if other_projects:
            violations.append(f"Cross-project contamination detected: {other_projects}")

        score = max(0.0, 1.0 - len(violations) * 0.25 - len(warnings) * 0.1)
        return {
            "consistent": len(violations) == 0,
            "score": score,
            "violations": violations,
            "warnings": warnings,
            "citations": citations,
        }

    async def verify_with_llm(
        self,
        query: str,
        answer: str,
        pack: ContextPack,
    ) -> Dict[str, any]:
        if not self.llm:
            return self.verify_answer(query, answer, pack)

        pack_text = "\n\n".join(
            f"[{s.section_name}]\n{s.content}" for s in pack.sections if s.content.strip()
        )
        system_prompt = (
            "You are a consistency verifier. Given a query, answer, and context pack, "
            "check if the answer is grounded in the pack and does not contradict active decisions. "
            "Return JSON: {consistent: bool, score: 0.0-1.0, violations: [string], warnings: [string]}"
        )
        user_prompt = f"Query: {query}\n\nAnswer: {answer}\n\nContext Pack:\n{pack_text[:6000]}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.llm.chat(messages, temperature=0.1, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            import json
            return json.loads(raw)
        except Exception:
            return self.verify_answer(query, answer, pack)

    def _contradicts(self, answer: str, decision: str) -> bool:
        # Simple heuristic: if decision keywords are in answer with negation
        dec_words = set(decision.lower().split())
        ans_words = set(answer.lower().split())
        overlap = len(dec_words & ans_words)
        # Naive: any overlap with explicit negation words suggests contradiction
        negation_words = {"not", "no", "never", "don't", "doesn't", "shouldn't", "avoid", "instead"}
        has_negation = len(negation_words & ans_words) > 0
        return overlap >= 1 and has_negation
