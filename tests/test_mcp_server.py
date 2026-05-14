import json

from vcm_os import mcp_server
from vcm_os.schemas.enums import MemoryType, SourceType, Validity
from vcm_os.schemas.memory import DecisionEntry, MemoryObject


class FakeStore:
    def __init__(self, memories):
        self._memories = memories

    def get_memories(self, project_id, limit=100, **kwargs):
        return [m for m in self._memories if m.project_id == project_id][:limit]


def test_get_project_state_handles_enum_fields(monkeypatch):
    statement = (
        "use VCM MCP state and preserve exact symbol "
        "KIMI_VCM_SMOKE_SYMBOL_THAT_MUST_NOT_BE_TRUNCATED_20260514"
    )
    decision = MemoryObject(
        memory_id="mem_decision",
        project_id="proj_mcp",
        memory_type=MemoryType.DECISION,
        source_type=SourceType.USER_MESSAGE,
        validity=Validity.ACTIVE,
        raw_text=f"Decision: {statement}",
        decisions=[DecisionEntry(statement=statement)],
    )

    monkeypatch.setattr(mcp_server, "_store", FakeStore([decision]))

    result = json.loads(mcp_server.vcm_get_project_state("proj_mcp"))

    assert result["total_memories"] == 1
    assert result["active_decisions"] == [
        {"id": "mem_decision", "text": statement}
    ]
