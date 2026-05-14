from typing import List, Optional

from vcm_os.llm_client import LLMClient
from vcm_os.schemas import MemoryObject, SessionIdentity
from vcm_os.storage.sqlite_store import SQLiteStore


class SummaryGenerator:
    def __init__(self, store: SQLiteStore, llm: LLMClient):
        self.store = store
        self.llm = llm

    async def generate_session_summary(self, session_id: str) -> str:
        mems = self.store.get_memories(session_id=session_id, limit=50)
        texts = []
        for m in mems:
            text = m.compressed_summary or m.raw_text or ""
            if text:
                texts.append(f"[{m.memory_type}] {text[:300]}")

        if not texts:
            return "No memories to summarize."

        context = "\n".join(texts)
        system_prompt = (
            "You are a session summarizer for a coding agent. "
            "Given a list of memory objects from a session, produce a concise summary (max 500 words) "
            "covering: goals, decisions, errors, code changes, open questions. "
            "Be factual and cite memory types."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context[:8000]},
        ]
        return await self.llm.chat(messages, temperature=0.3, max_tokens=1024)

    async def generate_project_summary(self, project_id: str) -> str:
        decisions = self.store.get_memories(project_id=project_id, memory_type="decision", validity="active", limit=20)
        errors = self.store.get_memories(project_id=project_id, memory_type="error", limit=10)
        reqs = self.store.get_memories(project_id=project_id, memory_type="requirement", limit=10)

        parts = []
        parts.append("ACTIVE DECISIONS:")
        for d in decisions:
            for dec in d.decisions:
                parts.append(f"- {dec.statement}")
        parts.append("\nRECENT ERRORS:")
        for e in errors:
            for err in e.errors_found:
                parts.append(f"- ({err.kind}) {err.message[:200]}")
        parts.append("\nREQUIREMENTS:")
        for r in reqs:
            text = r.compressed_summary or r.raw_text or ""
            parts.append(f"- {text[:200]}")

        context = "\n".join(parts)
        system_prompt = (
            "You are a project summarizer. Given active decisions, errors, and requirements, "
            "produce a high-level project state summary (max 400 words). Focus on what matters now."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context[:8000]},
        ]
        return await self.llm.chat(messages, temperature=0.3, max_tokens=1024)

    async def generate_file_summary(self, file_path: str, content: str) -> str:
        system_prompt = (
            "Summarize a code file in 2-3 sentences. Include: purpose, key classes/functions, dependencies."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content[:4000]},
        ]
        return await self.llm.chat(messages, temperature=0.2, max_tokens=256)
