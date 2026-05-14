"""Project State Object (PSO) schema v2."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProjectStateObject:
    project_id: str
    version: int = 0
    updated_at: str = ""

    # Core project state (v0.7)
    active_goals: List[str] = field(default_factory=list)
    open_tasks: List[str] = field(default_factory=list)
    current_architecture: List[str] = field(default_factory=list)
    latest_decisions: List[str] = field(default_factory=list)
    rejected_decisions: List[str] = field(default_factory=list)
    current_bugs: List[str] = field(default_factory=list)
    active_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    source_memory_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # v2 additions
    project_phase: str = ""  # e.g. "planning", "development", "testing", "deployment"
    current_branch: str = ""  # git branch
    current_milestone: str = ""  # e.g. "v1.0-rc2"
    blocked_tasks: List[str] = field(default_factory=list)  # tasks blocked by issues
    recently_changed_files: List[str] = field(default_factory=list)  # files from recent code_changes
    active_experiments: List[str] = field(default_factory=list)  # experimental features/branches
    test_status: str = ""  # e.g. "passing", "failing", "partial"
    deployment_status: str = ""  # e.g. "staging", "production", "rolled_back"
    risk_register: List[str] = field(default_factory=list)  # known risks/blockers

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "version": self.version,
            "updated_at": self.updated_at,
            "active_goals": self.active_goals,
            "open_tasks": self.open_tasks,
            "current_architecture": self.current_architecture,
            "latest_decisions": self.latest_decisions,
            "rejected_decisions": self.rejected_decisions,
            "current_bugs": self.current_bugs,
            "active_files": self.active_files,
            "dependencies": self.dependencies,
            "constraints": self.constraints,
            "source_memory_ids": self.source_memory_ids,
            "confidence": self.confidence,
            # v2
            "project_phase": self.project_phase,
            "current_branch": self.current_branch,
            "current_milestone": self.current_milestone,
            "blocked_tasks": self.blocked_tasks,
            "recently_changed_files": self.recently_changed_files,
            "active_experiments": self.active_experiments,
            "test_status": self.test_status,
            "deployment_status": self.deployment_status,
            "risk_register": self.risk_register,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectStateObject":
        return cls(
            project_id=d.get("project_id", ""),
            version=d.get("version", 0),
            updated_at=d.get("updated_at", ""),
            active_goals=d.get("active_goals", []),
            open_tasks=d.get("open_tasks", []),
            current_architecture=d.get("current_architecture", []),
            latest_decisions=d.get("latest_decisions", []),
            rejected_decisions=d.get("rejected_decisions", []),
            current_bugs=d.get("current_bugs", []),
            active_files=d.get("active_files", []),
            dependencies=d.get("dependencies", []),
            constraints=d.get("constraints", []),
            source_memory_ids=d.get("source_memory_ids", []),
            confidence=d.get("confidence", 0.0),
            # v2
            project_phase=d.get("project_phase", ""),
            current_branch=d.get("current_branch", ""),
            current_milestone=d.get("current_milestone", ""),
            blocked_tasks=d.get("blocked_tasks", []),
            recently_changed_files=d.get("recently_changed_files", []),
            active_experiments=d.get("active_experiments", []),
            test_status=d.get("test_status", ""),
            deployment_status=d.get("deployment_status", ""),
            risk_register=d.get("risk_register", []),
        )
