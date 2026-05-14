#!/usr/bin/env python3
"""Test VCM-OS CLI adapter with a single turn."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_cli_adapter import VCMCliAdapter


def test_single_turn():
    adapter = VCMCliAdapter(project_id="proj_auth", session_id="test_session_auth")

    query = "What decisions have we made about auth?"

    # Build context pack
    pack_text = adapter._build_context(query, token_budget=6000)
    print("=" * 60)
    print("CONTEXT PACK (proj_auth)")
    print("=" * 60)
    print(pack_text)
    print(f"\nPack size: {len(pack_text)} chars / ~{len(pack_text) // 4} tokens")
    print("=" * 60)

    # Call LLM
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Use the project context to answer accurately."},
        {"role": "user", "content": f"Project context:\n{pack_text}\n\nUser question: {query}"},
    ]

    print("\nCalling LLM...")
    response = adapter._call_llm(messages)
    print(f"\nLLM RESPONSE:\n{response}")


if __name__ == "__main__":
    test_single_turn()
