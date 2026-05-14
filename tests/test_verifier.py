"""Tests for Response Verifier v2."""
import pytest
from vcm_os.schemas import ContextPack, ContextPackSection, MemoryObject, MemoryType, SourceType, Validity, EntityRef
from vcm_os.verifier import ResponseVerifier


def test_verifier_detects_stale_fact():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")
    pack.sections = [ContextPackSection(section_name="decisions", content="old approach", token_estimate=5)]

    stale_mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        compressed_summary="old approach", validity=Validity.ARCHIVED,
    )

    result = v.verify("We should use old approach", pack, [stale_mem])
    assert result["violation_count"] == 1
    assert result["violations"][0]["type"] == "stale_usage"
    assert result["passed"] is False


def test_verifier_warns_unverified_file():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")
    pack.sections = [ContextPackSection(section_name="files", content="main.py", token_estimate=5)]

    mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.CODE_CHANGE, source_type=SourceType.CODE_DIFF,
        compressed_summary="main.py", file_references=["main.py"],
    )

    result = v.verify("Check utils.py for details", pack, [mem])
    assert result["warning_count"] >= 1
    assert any(w["type"] == "unverified_file" for w in result["warnings"])


def test_verifier_warns_no_citations():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")
    pack.sections = [ContextPackSection(section_name="facts", content="fact", token_estimate=5)]

    result = v.verify("This is a very long response without any memory citations or references to specific events and it keeps going on and on to make sure we exceed the threshold for citation checking which requires more than two hundred characters in total to trigger the no citations warning", pack, [])
    assert result["warning_count"] >= 1
    assert any(w["type"] == "no_citations" for w in result["warnings"])


def test_verifier_passes_clean_response():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")
    pack.sections = [ContextPackSection(section_name="decisions", content="use httpOnly", token_estimate=5)]

    mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        compressed_summary="use httpOnly", validity=Validity.ACTIVE,
        entities=[EntityRef(type="term", name="httpOnly")],
    )

    result = v.verify("We should use httpOnly cookies as per active decision (mem_abc123)", pack, [mem])
    assert result["passed"] is True
    assert result["score"] == 1.0


def test_verifier_detects_rejected_decision_revival():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")

    mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        compressed_summary="use Redis for caching", validity=Validity.REJECTED,
        decisions=[{"statement": "use Redis for caching"}],
    )

    result = v.verify("We should use Redis for caching", pack, [mem])
    assert result["violation_count"] == 1
    assert result["violations"][0]["type"] == "rejected_decision_revival"


def test_verifier_detects_tool_contradiction():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")

    tool_mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.FACT, source_type=SourceType.TOOL_OUTPUT,
        compressed_summary="pytest: 10 passed, 0 failed", raw_text="pytest: 10 passed, 0 failed",
    )

    result = v.verify("The tests failed because of a bug", pack, [tool_mem])
    assert result["violation_count"] == 1
    assert result["violations"][0]["type"] == "tool_evidence_mismatch"


def test_verifier_warns_unsupported_strong_claim():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")

    result = v.verify("We must never use this approach under any circumstances because it is definitely broken", pack, [])
    assert any(w["type"] == "unsupported_strong_claim" for w in result["warnings"])


def test_verifier_warns_unverified_symbol():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")

    mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.CODE_CHANGE, source_type=SourceType.CODE_DIFF,
        compressed_summary="Fixed AuthService", entities=[EntityRef(type="class", name="AuthService")],
    )

    result = v.verify("Use UserManager instead of AuthService", pack, [mem])
    assert any(w["type"] == "unverified_symbol" for w in result["warnings"])


def test_verifier_detects_active_decision_contradiction():
    v = ResponseVerifier()
    pack = ContextPack(project_id="proj1", session_id="sess1")

    mem = MemoryObject(
        project_id="proj1", memory_type=MemoryType.DECISION, source_type=SourceType.USER_MESSAGE,
        compressed_summary="use PostgreSQL for main DB", validity=Validity.ACTIVE,
        decisions=[{"statement": "use PostgreSQL for main DB"}],
    )

    result = v.verify("We no longer use PostgreSQL for main DB", pack, [mem])
    assert result["violation_count"] == 1
    assert result["violations"][0]["type"] == "active_decision_contradiction"
