from vcm_os.schemas import MemoryObject, MemoryType, SourceType


class ScorerMixin:
    def _score_importance(self, obj: MemoryObject) -> float:
        score = 0.5
        if obj.memory_type == MemoryType.DECISION:
            score += 0.3
        if obj.memory_type == MemoryType.ERROR:
            score += 0.25
        if obj.source_type == SourceType.USER_MESSAGE:
            score += 0.1
        if obj.file_references:
            score += 0.05
        if obj.decisions:
            score += 0.1
        return min(1.0, score)

    def _score_confidence(self, obj: MemoryObject) -> float:
        if obj.source_type == SourceType.USER_MESSAGE:
            return 0.9
        if obj.source_type == SourceType.TOOL_OUTPUT:
            return 0.85
        if obj.source_type == SourceType.ASSISTANT_MESSAGE:
            return 0.5
        return 0.5
