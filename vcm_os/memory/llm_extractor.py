"""LLM-powered structured memory extraction from raw events.

Falls back to rule-based extraction if LLM is unavailable or returns invalid JSON.
"""

import json
import os
import re
from typing import Dict, List, Optional

import requests


EXTRACTION_PROMPT = """You are a memory extraction system for a coding agent. Given a raw event from a development session, extract structured memory objects.

Event type: {event_type}
Text: {text}

Extract ALL of the following that apply:
1. **decisions** — explicit or implicit decisions, architectural choices, technology selections
2. **errors** — bugs, test failures, runtime errors, with kind and message
3. **requirements** — user requirements, constraints, must/should/need statements
4. **intents** — user goals, what they want to achieve
5. **code_change** — file modifications, with file paths
6. **uncertainty** — open questions, unknowns, risks
7. **task** — TODO items, planned work
8. **fact** — verified facts, observations

For each object, provide:
- memory_type: one of [decision, error, requirement, intent, code_change, uncertainty, task, fact]
- summary: concise 1-2 sentence description
- rationale: why this matters (for decisions)
- entities: list of {{"type": "file|function|class|concept|api", "name": "..."}}
- file_references: list of file paths mentioned
- importance: 0.0-1.0 (how critical is this?)
- confidence: 0.0-1.0 (how certain are you?)

For errors, also include:
- error_kind: test_failure | runtime_error | compile_error | lint_error | security_error
- error_message: the exact error text

For decisions, also include:
- alternatives: other options considered (if any)
- status: active | proposed | rejected

Return ONLY a JSON array of objects. No markdown, no explanation.

Example:
[
  {{
    "memory_type": "decision",
    "summary": "Use httpOnly cookie for refresh token",
    "rationale": "Reduces XSS exposure",
    "entities": [{{"type": "concept", "name": "httpOnly"}}],
    "file_references": ["src/auth/session.ts"],
    "importance": 0.9,
    "confidence": 0.95,
    "alternatives": ["LocalStorage"],
    "status": "active"
  }},
  {{
    "memory_type": "error",
    "summary": "refreshSession called repeatedly in middleware",
    "error_kind": "test_failure",
    "error_message": "tests/auth.test.ts still failing: refreshSession called repeatedly",
    "importance": 0.85,
    "confidence": 0.9
  }}
]
"""


class LLMExtractor:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("VLLM_URL", "http://localhost:8000/v1")
        self.model = model or os.getenv("VLLM_MODEL", "google/gemma-4-31b-it")
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=2)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def extract(self, event_type: str, text: str) -> List[Dict]:
        if not self.is_available():
            return []

        prompt = EXTRACTION_PROMPT.format(event_type=event_type, text=text[:2000])

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a structured memory extraction engine. Output valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_json(content)
        except Exception:
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        # Try to extract JSON array from markdown code block or raw text
        text = text.strip()
        # Remove markdown code blocks
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "objects" in parsed:
                return parsed["objects"]
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            pass

        # Try regex extraction of JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        return []
