"""Tests for pack sufficiency verifier."""
from vcm_os.schemas import ContextPack, ContextPackSection, DecisionEntry, MemoryObject, SourceType, Validity
from vcm_os.verifier.pack_sufficiency import PackSufficiencyVerifier


def _pack(text: str, memory_id: str = "mem_abc123") -> ContextPack:
    return ContextPack(
        project_id="p1",
        sections=[ContextPackSection(section_name="exact_symbols", content=text, source_memory_id=memory_id)],
    )


def _mem(memory_type: str = "fact", decisions=None, source_type=SourceType.TOOL_OUTPUT) -> MemoryObject:
    return MemoryObject(
        memory_id="m1", project_id="p1", session_id="s1",
        memory_type=memory_type, source_type=source_type,
        decisions=decisions or [],
    )


def test_sufficient_pack():
    verifier = PackSufficiencyVerifier()
    pack = _pack("Decision: use Redis for caching. mem_abc123")
    mems = [_mem("decision", [DecisionEntry(statement="use Redis", status=Validity.ACTIVE)])]
    result = verifier.verify("What was the caching decision?", pack, mems)
    assert result["sufficient"] is True
    assert result["score"] >= 0.7


def test_missing_keyword():
    verifier = PackSufficiencyVerifier()
    pack = _pack("Decision: use Redis for caching. mem_abc123")
    mems = [_mem("decision", [DecisionEntry(statement="use Redis", status=Validity.ACTIVE)])]
    result = verifier.verify("What was the database decision?", pack, mems)
    assert result["sufficient"] is False or result["score"] < 1.0
    assert any(i["type"] == "keyword_gap" for i in result["issues"])


def test_missing_memory_type():
    verifier = PackSufficiencyVerifier()
    pack = _pack("Some general info. mem_abc123")
    mems = [_mem("fact")]
    result = verifier.verify("What errors occurred?", pack, mems)
    assert any(i["type"] == "missing_memory_type" for i in result["issues"])


def test_pack_too_short():
    verifier = PackSufficiencyVerifier()
    pack = _pack("hi")
    mems = [_mem("fact")]
    result = verifier.verify("What is the state?", pack, mems)
    assert any(i["type"] == "pack_too_short" for i in result["issues"])


def test_internal_contradiction():
    verifier = PackSufficiencyVerifier()
    pack = _pack("Decision: use Redis cache. Decision: rejected use Redis cache. mem_abc123")
    mems = [
        _mem("decision", [DecisionEntry(statement="use Redis cache", status=Validity.ACTIVE)]),
        _mem("decision", [DecisionEntry(statement="use Redis cache", status=Validity.REJECTED)]),
    ]
    result = verifier.verify("What was decided?", pack, mems)
    assert any(i["type"] == "internal_contradiction" for i in result["issues"])


def test_low_diversity():
    verifier = PackSufficiencyVerifier()
    pack = _pack("a b c d e f g h i j k l m n o p q r s t. mem_abc123")
    mems = [_mem("fact") for _ in range(5)]
    result = verifier.verify("What happened?", pack, mems)
    assert any(i["type"] == "low_diversity" for i in result["issues"])


def test_no_citations():
    verifier = PackSufficiencyVerifier()
    pack = _pack("Some info without any memory reference")
    mems = [_mem("fact")]
    result = verifier.verify("What is the state?", pack, mems)
    assert any(i["type"] == "no_citations_in_pack" for i in result["issues"])
