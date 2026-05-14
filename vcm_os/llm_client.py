import json
import os
from typing import Any, Dict, List, Optional

import httpx


class LLMClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.base_url = (base_url or os.getenv("VCM_LLM_URL", "http://localhost:8000/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("VCM_LLM_API_KEY", "")
        self.model = model or os.getenv("VCM_LLM_MODEL", "google/gemma-4-31B-it")
        self.embedding_model = embedding_model or os.getenv("VCM_EMBEDDING_API_MODEL", "gen2b/embedding")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        resp = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self.embedding_model,
            "input": texts,
        }
        resp = await self._client.post(
            f"{self.base_url}/embeddings",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    async def extract_memory_objects(
        self,
        event_text: str,
        event_type: str,
    ) -> List[Dict[str, Any]]:
        system_prompt = (
            "You are a structured memory extraction system. "
            "Given an event text and type, extract typed memory objects as JSON list. "
            "Each object must have fields: memory_type (one of: decision, error, requirement, fact, intent, task, code_change, uncertainty, preference, procedure), "
            "summary (string), importance (0.0-1.0), confidence (0.0-1.0), "
            "entities (list of {type, name}), file_references (list of strings). "
            "Return ONLY a JSON array. No markdown."
        )
        user_prompt = f"Event type: {event_type}\n\nEvent text:\n{event_text[:4000]}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.chat(messages, temperature=0.1, max_tokens=2048)
            # Strip markdown if present
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            return json.loads(raw)
        except Exception:
            return []

    async def rewrite_query(self, query: str, task_type: str) -> List[str]:
        system_prompt = (
            "You are a query expansion system for a coding agent memory retrieval. "
            "Given a user query and task type, generate 2-3 alternative search queries "
            "that would help retrieve relevant memories. Return ONLY a JSON array of strings."
        )
        user_prompt = f"Task type: {task_type}\nQuery: {query}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.chat(messages, temperature=0.3, max_tokens=256)
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            queries = json.loads(raw)
            if isinstance(queries, list):
                return [q for q in queries if isinstance(q, str)]
        except Exception:
            pass
        return [query]

    async def check_sufficiency(
        self,
        query: str,
        pack_text: str,
    ) -> Dict[str, Any]:
        system_prompt = (
            "You evaluate whether a context pack contains sufficient information to answer a query. "
            "Return JSON with fields: sufficient (bool), score (0.0-1.0), missing (list of strings)."
        )
        user_prompt = f"Query: {query}\n\nContext Pack:\n{pack_text[:6000]}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.chat(messages, temperature=0.1, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            return json.loads(raw)
        except Exception:
            return {"sufficient": True, "score": 0.5, "missing": []}

    async def generate_reflection(
        self,
        evidence_texts: List[str],
    ) -> Optional[Dict[str, Any]]:
        if len(evidence_texts) < 3:
            return None
        system_prompt = (
            "Given a list of related events/decisions/errors from a coding project, "
            "generate a high-level reflection/lesson learned. "
            "Return JSON with: reflection_text (string), claims (list of strings), confidence (0.0-1.0). "
            "If evidence is too weak, return null."
        )
        user_prompt = "Evidence:\n" + "\n---\n".join(evidence_texts[:10])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.chat(messages, temperature=0.3, max_tokens=1024)
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            if raw.lower() in ("null", "none", ""):
                return None
            return json.loads(raw)
        except Exception:
            return None

    async def close(self):
        await self._client.aclose()
