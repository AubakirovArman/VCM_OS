"""VCM Gateway — LLM proxy with memory injection and verification.

Intercepts OpenAI-compatible chat completion requests, injects VCM memory
pack into the system prompt, forwards to the backend LLM, verifies the
response, and persists the conversation to memory.
"""
import json
import os
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

import vcm_os.app.state as state
from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.verifier import ResponseVerifier

router = APIRouter()

LLM_API_BASE = os.getenv("VCM_GATEWAY_LLM_API_BASE", os.getenv("VCM_LLM_URL", "http://localhost:8000/v1")).rstrip("/")
LLM_API_KEY = os.getenv("VCM_GATEWAY_LLM_API_KEY", os.getenv("VCM_LLM_API_KEY", ""))


def _llm_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    return headers


def _extract_query(messages: List[Dict[str, str]]) -> str:
    """Use the last user message as the VCM query."""
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _inject_memory_pack(
    messages: List[Dict[str, str]],
    pack_text: str,
    sufficiency: float,
) -> List[Dict[str, str]]:
    """Insert VCM memory pack as a system message before the conversation."""
    out = []
    # System message with VCM context
    vcm_system = (
        f"[VCM Memory Pack — sufficiency={sufficiency:.2f}]\n"
        f"{pack_text}\n"
        f"[End VCM Memory Pack]"
    )
    out.append({"role": "system", "content": vcm_system})
    # Copy original messages, keeping existing system messages after VCM
    for m in messages:
        out.append(m)
    return out


async def _forward_to_llm(body: Dict[str, Any]) -> Dict[str, Any]:
    """Forward the (possibly modified) request to the backend LLM API."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{LLM_API_BASE}/chat/completions", json=body, headers=_llm_headers())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


async def _forward_to_llm_streaming(body: Dict[str, Any]):
    """Stream the response from the backend LLM."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", f"{LLM_API_BASE}/chat/completions", json=body, headers=_llm_headers()) as resp:
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=await resp.aread())
            async for chunk in resp.aiter_text():
                yield chunk


@router.post("/gateway/chat/completions")
async def gateway_chat_completions(
    request: Request,
    x_project_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    x_vcm_budget: int = Header(500),
):
    """Proxy chat completions through VCM memory layer.

    Headers:
        x-project-id:   Project identifier for memory scope (required)
        x-session-id:   Session identifier (optional, auto-generated if missing)
        x-vcm-budget:   Max pack tokens (default 500)
    """
    body = await request.json()
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    project_id = x_project_id or body.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="x-project-id header or project_id field required")

    session_id = x_session_id or body.get("session_id") or f"sess_{uuid.uuid4().hex[:8]}"

    # 1. Build VCM memory pack
    query = _extract_query(messages)
    mem_request = MemoryRequest(
        project_id=project_id,
        session_id=session_id,
        query=query,
        task_type=body.get("task_type", "general"),
        token_budget=8192,
        max_pack_tokens=x_vcm_budget,
    )

    plan = state.router.make_plan(mem_request)
    candidates = state.reader.retrieve(mem_request, plan)
    scored = state.scorer.rerank(candidates, mem_request)
    memories = [m for m, _ in scored[:50]]
    pack = state.pack_builder.build(mem_request, memories)
    pack_text = "\n".join(s.content for s in pack.sections if s.content.strip())

    # 2. Inject pack into messages
    modified_messages = _inject_memory_pack(messages, pack_text, pack.sufficiency_score)
    body["messages"] = modified_messages

    # Remove VCM-specific fields before forwarding
    body.pop("project_id", None)
    body.pop("session_id", None)
    body.pop("task_type", None)

    # 3. Persist user message to VCM
    user_msg = _extract_query(messages)
    if user_msg:
        state.writer.capture_event(EventRecord(
            event_id=f"evt_user_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            session_id=session_id,
            event_type="user_message",
            payload={"role": "user", "content": user_msg},
            raw_text=user_msg,
        ))

    # 4. Forward to LLM
    stream = body.get("stream", False)
    if stream:
        # For streaming, we can't easily verify until the full response is assembled.
        # For now, return the stream as-is and ingest afterwards in a fire-and-forget way.
        return StreamingResponse(
            _forward_to_llm_streaming(body),
            media_type="text/event-stream",
        )

    llm_resp = await _forward_to_llm(body)

    # 5. Extract assistant response
    assistant_text = ""
    choices = llm_resp.get("choices", [])
    if choices:
        assistant_text = choices[0].get("message", {}).get("content", "")

    # 6. Verify response
    verifier = ResponseVerifier()
    vresult = verifier.verify(assistant_text, pack, memories)

    # 7. Persist assistant response to VCM
    if assistant_text:
        state.writer.capture_event(EventRecord(
            event_id=f"evt_assistant_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            session_id=session_id,
            event_type="assistant_response",
            payload={
                "role": "assistant",
                "content": assistant_text,
                "verifier_passed": vresult["passed"],
                "verifier_score": vresult["score"],
                "pack_sufficiency": pack.sufficiency_score,
            },
            raw_text=assistant_text,
        ))

    # 8. Add VCM metadata to response
    llm_resp["vcm"] = {
        "project_id": project_id,
        "session_id": session_id,
        "pack_sufficiency": pack.sufficiency_score,
        "pack_tokens": pack.token_estimate,
        "verifier_passed": vresult["passed"],
        "verifier_score": vresult["score"],
        "verifier_violations": vresult.get("violations", []),
        "verifier_warnings": vresult.get("warnings", []),
    }

    return llm_resp
