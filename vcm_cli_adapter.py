#!/usr/bin/env python3
"""VCM-OS CLI Adapter — integrates VCM memory into live coding workflow.

Usage:
    python vcm_cli_adapter.py --project my_project --session sess_001

This creates a simple REPL where:
1. User input is recorded as VCM event
2. Context pack is retrieved from VCM-OS
3. Pack + query are sent to LLM (localhost:8000)
4. LLM response is recorded as VCM event
5. Response is shown to user
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_os.memory.writer import MemoryWriter
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.memory.project_state import ProjectStateExtractor, ProjectStateSlot, ProjectStateStore
from vcm_os.memory.symbol_vault import SymbolVaultStore, SymbolVaultSlot, SymbolVaultRetriever
from vcm_os.schemas import EventRecord, MemoryRequest, SessionIdentity, SessionState
from vcm_os.session.store import SessionStore
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


class VCMCliAdapter:
    def __init__(self, project_id: str, session_id: str = None):
        self.project_id = project_id
        self.session_id = session_id or f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.session_title = f"Session {self.session_id}"

        # Init VCM-OS components
        self.store = SQLiteStore()
        self.vi = VectorIndex()
        self.si = SparseIndex()
        self.writer = MemoryWriter(self.store, self.vi, self.si)
        self.reader = MemoryReader(self.store, self.vi, self.si)
        self.router = MemoryRouter()
        self.scorer = MemoryScorer(self.vi)
        self.pack_builder = ContextPackBuilder()
        self.session_store = SessionStore(self.store)
        self.pso_extractor = ProjectStateExtractor()
        self.pso_store = ProjectStateStore(self.store)
        self.symbol_vault_store = SymbolVaultStore(self.store)
        self.symbol_vault_slot = SymbolVaultSlot(SymbolVaultRetriever(self.symbol_vault_store))

        # Create or load session
        existing = self.session_store.get_session(self.session_id)
        if not existing:
            sess = self.session_store.create_session(
                project_id=self.project_id,
                title=self.session_title,
            )
            self.session_id = sess.session_id

        # LLM endpoint
        self.llm_url = os.environ.get("VCM_LLM_URL", "http://localhost:8000/v1/chat/completions")
        self.llm_model = os.environ.get("VCM_LLM_MODEL", "google/gemma-4-31B-it")
        self.llm_api_key = os.environ.get("VCM_LLM_API_KEY", "")

    def _call_llm(self, messages: list) -> str:
        """Call LLM with messages."""
        headers = {"Content-Type": "application/json"}
        if self.llm_api_key:
            headers["Authorization"] = f"Bearer {self.llm_api_key}"

        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        try:
            resp = requests.post(self.llm_url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM Error: {e}]"

    def _build_context(self, query: str, token_budget: int = 6000) -> str:
        """Build context pack and return as text."""
        request = MemoryRequest(
            project_id=self.project_id,
            query=query,
            token_budget=token_budget,
            task_type=self.router.classify_task(query),
        )

        plan = self.router.make_plan(request)
        candidates = self.reader.retrieve(request, plan)
        scored = self.scorer.rerank(candidates, request)
        memories = [m for m, _ in scored[:50]]

        # PSO
        mems = self.store.get_memories(project_id=self.project_id, limit=500)
        pso = self.pso_extractor.extract(mems)
        self.pso_store.save(pso)
        pso_text = ProjectStateSlot(self.pso_store).get_slot_text(
            self.project_id,
            stale_terms=[],
        )

        # Symbol vault
        sv_text = self.symbol_vault_slot.get_slot_text(
            self.project_id,
            query,
            required_terms=[],
        )

        # Load session state
        session = self.session_store.get_session(self.session_id)
        active_state = SessionState(
            session_id=self.session_id,
            recent_decisions=pso.latest_decisions[-3:] if pso else [],
            recent_errors=pso.current_bugs[-3:] if pso else [],
            active_files=pso.active_files[:5] if pso else [],
            open_tasks=pso.open_tasks[:5] if pso else [],
        )

        pack = self.pack_builder.build(
            request, memories,
            active_state=active_state,
            session=session,
            project_state_text=pso_text or None,
            symbol_vault_text=sv_text or None,
        )

        # Render pack as context string
        context_parts = []
        for sec in pack.sections:
            if sec.content.strip():
                context_parts.append(sec.content)
        return "\n\n".join(context_parts)

    def run_repl(self):
        """Run interactive REPL."""
        print(f"VCM-OS CLI Adapter")
        print(f"Project: {self.project_id} | Session: {self.session_id}")
        print(f"LLM: {self.llm_model} @ {self.llm_url}")
        print("Type 'exit' to quit, 'pack' to see current context pack")
        print("-" * 60)

        turn = 0
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if not user_input:
                continue
            if user_input.lower() == "exit":
                print("Saving session...")
                self.session_store.save_checkpoint(self.session_id)
                break
            if user_input.lower() == "pack":
                pack_text = self._build_context("current context", token_budget=6000)
                print(f"\n--- Context Pack ({len(pack_text)} chars) ---")
                print(pack_text[:800])
                print("..." if len(pack_text) > 800 else "")
                continue

            turn += 1
            event_id = f"evt_{self.session_id}_{turn}"

            # Record user message
            event = EventRecord(
                event_id=event_id,
                project_id=self.project_id,
                session_id=self.session_id,
                event_type="user_message",
                raw_text=user_input,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.writer.capture_event(event)

            # Build context
            pack_text = self._build_context(user_input, token_budget=6000)

            # Call LLM
            messages = [
                {"role": "system", "content": "You are a helpful coding assistant. Use the provided project context to answer accurately."},
                {"role": "user", "content": f"Project context:\n{pack_text}\n\nUser question: {user_input}"},
            ]

            print("\n[Building context pack...]")
            print(f"[Calling LLM...]")

            response = self._call_llm(messages)

            # Record assistant response
            resp_event = EventRecord(
                event_id=f"{event_id}_resp",
                project_id=self.project_id,
                session_id=self.session_id,
                event_type="assistant_response",
                raw_text=response,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.writer.capture_event(resp_event)

            # Update PSO
            mems = self.store.get_memories(project_id=self.project_id, limit=500)
            pso = self.pso_extractor.extract(mems)
            self.pso_store.save(pso)

            print(f"\nAssistant: {response}")


def main():
    parser = argparse.ArgumentParser(description="VCM-OS CLI Adapter")
    parser.add_argument("--project", default="default_project", help="Project ID")
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if not set)")
    args = parser.parse_args()

    adapter = VCMCliAdapter(project_id=args.project, session_id=args.session)
    adapter.run_repl()


if __name__ == "__main__":
    main()
