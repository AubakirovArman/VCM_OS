"""Core trace data structures for VCM pipeline introspection."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TraceEvent:
    stage: str  # e.g. "router", "reader", "scorer", "pack_builder", "rescue"
    action: str  # e.g. "plan_created", "retrieved", "reranked", "budget_allocated", "dropped", "included"
    memory_id: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class TraceLog:
    query: str = ""
    project_id: str = ""
    events: List[TraceEvent] = field(default_factory=list)

    def add(self, stage: str, action: str, memory_id: Optional[str] = None, details: Optional[Dict] = None) -> None:
        self.events.append(TraceEvent(
            stage=stage,
            action=action,
            memory_id=memory_id,
            details=details or {},
        ))

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "project_id": self.project_id,
            "events": [
                {
                    "stage": e.stage,
                    "action": e.action,
                    "memory_id": e.memory_id,
                    "details": e.details,
                }
                for e in self.events
            ],
        }

    def drops(self) -> List[TraceEvent]:
        return [e for e in self.events if e.action == "dropped"]

    def inclusions(self) -> List[TraceEvent]:
        return [e for e in self.events if e.action == "included"]

    def unexplained_drops(self) -> List[TraceEvent]:
        """Drops without a detailed reason."""
        return [e for e in self.drops() if not e.details.get("reason")]
