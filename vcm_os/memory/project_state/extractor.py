"""Extract Project State Object deltas from memory writes."""
import re
from typing import List

from vcm_os.memory.project_state.schema import ProjectStateObject
from vcm_os.schemas import MemoryObject


_PHASE_KEYWORDS = {
    "planning": ["plan", "design", "architecture", "roadmap"],
    "development": ["implement", "code", "build", "develop", "feature"],
    "testing": ["test", "qa", "validate", "verify", "pytest", "jest"],
    "deployment": ["deploy", "release", "staging", "production", "rollout"],
    "maintenance": ["fix", "patch", "update", "maintain", "refactor"],
}

_TEST_STATUS_KEYWORDS = {
    "passing": ["passed", "green", "all tests pass", "success"],
    "failing": ["failed", "red", "test failure", "broken"],
    "partial": ["some tests", "partial", "flaky"],
}

_DEPLOY_STATUS_KEYWORDS = {
    "staging": ["staging", "preview", "dev"],
    "production": ["production", "prod", "live"],
    "rolled_back": ["rollback", "revert", "rolled back"],
}


class ProjectStateExtractor:
    """Derive project-state deltas from typed memory objects."""

    def extract(self, memories: List[MemoryObject]) -> ProjectStateObject:
        """Build a PSO from a batch of memory objects."""
        if not memories:
            return ProjectStateObject(project_id="")

        project_id = memories[0].project_id
        pso = ProjectStateObject(project_id=project_id)

        # Track recency for recently_changed_files
        recent_files = []

        for mem in memories:
            pso.source_memory_ids.append(mem.memory_id)
            mt = mem.memory_type
            text = mem.compressed_summary or mem.raw_text or ""
            text_lower = text.lower()

            # Generic field extraction from any memory type
            if "branch" in text_lower:
                branch = self._extract_branch(text)
                if branch:
                    pso.current_branch = branch
            if "milestone" in text_lower:
                milestone = self._extract_milestone(text)
                if milestone:
                    pso.current_milestone = milestone
            if any(k in text_lower for k in ["blocked", "blocking", "cannot proceed", "waiting for"]):
                blocked = self._extract_blocked(text)
                if blocked:
                    pso.blocked_tasks.append(blocked)
            if any(k in text_lower for k in ["risk", "danger", "critical issue", "concern"]):
                risk = self._extract_risk(text)
                if risk:
                    pso.risk_register.append(risk)

            if mt == "decision":
                clean = text.strip()
                for prefix in ("Proposed decision: ", "Decision: ", "Rejected decision: "):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):].strip()
                        break
                pso.latest_decisions.append(clean)
                # Check for milestone/phase in decisions
                if "milestone" in text_lower:
                    pso.current_milestone = self._extract_milestone(text)
                if "phase" in text_lower:
                    phase = self._detect_phase(text_lower)
                    if phase:
                        pso.project_phase = phase
            elif mt == "error":
                clean = text.strip()
                for prefix in ("Error: ", "Error (test_failure): ", "Error (runtime_error): ", "Error (tool_error): "):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):].strip()
                        break
                pso.current_bugs.append(clean)
                # Blocked tasks from errors
                if any(k in text_lower for k in ["blocked", "blocking", "cannot proceed"]):
                    pso.blocked_tasks.append(text.strip()[:80])
                # Risk register
                if any(k in text_lower for k in ["risk", "danger", "critical issue"]):
                    pso.risk_register.append(text.strip()[:80])
            elif mt == "requirement":
                clean = text.strip()
                for prefix in ("Requirement: ", "Goal: ", "Need to "):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):].strip()
                        break
                pso.active_goals.append(clean)
                phase = self._detect_phase(text_lower)
                if phase:
                    pso.project_phase = phase
            elif mt == "task":
                clean = text.strip()
                for prefix in ("Task: ", "Open task: ", "Assistant plan: "):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):].strip()
                        break
                pso.open_tasks.append(clean)
                if any(k in text_lower for k in ["blocked", "blocking", "waiting for"]):
                    pso.blocked_tasks.append(text.strip()[:80])
            elif mt == "code_change":
                for fp in mem.file_references:
                    pso.active_files.append(fp)
                    recent_files.append(fp)
                # Branch from code_change metadata
                if hasattr(mem, "metadata") and mem.metadata:
                    branch = mem.metadata.get("branch") if isinstance(mem.metadata, dict) else None
                    if branch:
                        pso.current_branch = branch
                # Deployment status from commit/deploy
                if any(k in text_lower for k in ["deploy", "release"]):
                    deploy = self._detect_deploy_status(text_lower)
                    if deploy:
                        pso.deployment_status = deploy
            elif mt == "dependency":
                pso.dependencies.append(text.strip())
            elif mt == "constraint":
                pso.constraints.append(text.strip())
            elif mt == "uncertainty":
                if any(k in text_lower for k in ["risk", "concern", "uncertain"]):
                    pso.risk_register.append(text.strip()[:80])
            elif mt == "intent":
                phase = self._detect_phase(text_lower)
                if phase:
                    pso.project_phase = phase
                if any(k in text_lower for k in ["experiment", "spike", "prototype", "poc"]):
                    pso.active_experiments.append(text.strip()[:80])
            elif mt == "fact" or mt == "test_result":
                test_status = self._detect_test_status(text_lower)
                if test_status:
                    pso.test_status = test_status
            elif mt == "tool_call":
                test_status = self._detect_test_status(text_lower)
                if test_status:
                    pso.test_status = test_status
                deploy = self._detect_deploy_status(text_lower)
                if deploy:
                    pso.deployment_status = deploy

        # Keep last 5 recently changed files
        pso.recently_changed_files = list(dict.fromkeys(recent_files))[-5:]

        # Deduplicate all lists
        for field_name in [
            "latest_decisions", "current_bugs", "active_goals", "open_tasks",
            "active_files", "dependencies", "constraints", "blocked_tasks",
            "active_experiments", "risk_register",
        ]:
            setattr(pso, field_name, list(dict.fromkeys(getattr(pso, field_name))))

        pso.confidence = 0.7
        return pso

    def _detect_phase(self, text_lower: str) -> str:
        for phase, keywords in _PHASE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return phase
        return ""

    def _detect_test_status(self, text_lower: str) -> str:
        for status, keywords in _TEST_STATUS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return status
        return ""

    def _detect_deploy_status(self, text_lower: str) -> str:
        for status, keywords in _DEPLOY_STATUS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return status
        return ""

    def _extract_milestone(self, text: str) -> str:
        m = re.search(r"milestone[\s:]+([^\n.]{3,40})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_branch(self, text: str) -> str:
        m = re.search(r"branch[\s:]+([^\n.]{3,40})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_blocked(self, text: str) -> str:
        m = re.search(r"blocked[\s:]+([^\n]{5,80})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_risk(self, text: str) -> str:
        m = re.search(r"risk[\s:]+([^\n]{5,80})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    def merge(self, old: ProjectStateObject, delta: ProjectStateObject) -> ProjectStateObject:
        """Merge a delta into an existing PSO."""
        merged = ProjectStateObject(
            project_id=old.project_id,
            version=old.version + 1,
            updated_at=delta.updated_at,
        )
        # Append new items, preserving order
        merged.active_goals = old.active_goals + [g for g in delta.active_goals if g not in old.active_goals]
        merged.open_tasks = old.open_tasks + [t for t in delta.open_tasks if t not in old.open_tasks]
        merged.latest_decisions = old.latest_decisions + [d for d in delta.latest_decisions if d not in old.latest_decisions]
        merged.rejected_decisions = old.rejected_decisions + [d for d in delta.rejected_decisions if d not in old.rejected_decisions]
        merged.current_bugs = old.current_bugs + [b for b in delta.current_bugs if b not in old.current_bugs]
        merged.active_files = old.active_files + [f for f in delta.active_files if f not in old.active_files]
        merged.dependencies = old.dependencies + [d for d in delta.dependencies if d not in old.dependencies]
        merged.constraints = old.constraints + [c for c in delta.constraints if c not in old.constraints]
        merged.source_memory_ids = old.source_memory_ids + delta.source_memory_ids
        merged.confidence = (old.confidence + delta.confidence) / 2.0
        # v2 fields
        merged.blocked_tasks = old.blocked_tasks + [b for b in delta.blocked_tasks if b not in old.blocked_tasks]
        merged.recently_changed_files = list(dict.fromkeys(old.recently_changed_files + delta.recently_changed_files))[-5:]
        merged.active_experiments = old.active_experiments + [e for e in delta.active_experiments if e not in old.active_experiments]
        merged.risk_register = old.risk_register + [r for r in delta.risk_register if r not in old.risk_register]
        # Overwrite scalar fields if delta has them
        if delta.project_phase:
            merged.project_phase = delta.project_phase
        if delta.current_branch:
            merged.current_branch = delta.current_branch
        if delta.current_milestone:
            merged.current_milestone = delta.current_milestone
        if delta.test_status:
            merged.test_status = delta.test_status
        if delta.deployment_status:
            merged.deployment_status = delta.deployment_status
        return merged
