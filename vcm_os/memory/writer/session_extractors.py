"""Extract goals and errors from real session logs."""
import re
from typing import List, Optional


class SessionGoalExtractor:
    """Extract goals from noisy session log text."""

    GOAL_PATTERNS = [
        re.compile(r"(?:we need to|we should|we must|we want to|we have to)\s+(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:next we should|next we need to|then we should)\s+(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:the goal is|our goal is|the objective is)\s+(?:to\s+)?(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:let's fix|let's implement|let's add|let's refactor)\s+(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:need to investigate|need to debug|need to fix|need to implement)\s+(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:continue from|continue working on|resume work on)\s+(.{5,200})", re.IGNORECASE),
        re.compile(r"(?:priority|blocker|must have|should have)\s*[:-]?\s*(.{5,200})", re.IGNORECASE),
    ]

    # Filter out assistant speculation/planning
    SKIP_PATTERNS = [
        re.compile(r"^(?:I think|Maybe|Perhaps|It might|One option|Alternatively)", re.IGNORECASE),
        re.compile(r"^(?:If we|We could|We might|Another idea|Let's consider)", re.IGNORECASE),
    ]

    def extract(self, text: str) -> List[str]:
        """Extract goal statements from session text."""
        goals = []
        for pattern in self.GOAL_PATTERNS:
            for match in pattern.finditer(text):
                goal = match.group(1).strip()
                if len(goal) < 5:
                    continue
                if self._is_speculation(goal):
                    continue
                # Clean up trailing punctuation
                goal = re.sub(r"[.!?;,]+$", "", goal)
                goals.append(goal)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for g in goals:
            key = g.lower()
            if key not in seen:
                seen.add(key)
                unique.append(g)
        return unique[:5]

    def _is_speculation(self, text: str) -> bool:
        for pattern in self.SKIP_PATTERNS:
            if pattern.match(text):
                return True
        return False


class SessionErrorExtractor:
    """Extract errors from noisy session log text."""

    ERROR_PATTERNS = [
        re.compile(r"(?:failed because|error:|error\s+\(|exception:|bug:|crash:|panic:|segfault:?)\s*(.{5,300})", re.IGNORECASE),
        re.compile(r"(?:test failed|tests failed|build failed|deploy failed)\s*(.{5,300})", re.IGNORECASE),
        re.compile(r"(?:got error|got an error|encountered error|ran into error)\s*(.{5,300})", re.IGNORECASE),
        re.compile(r"(?:traceback|stack trace|stacktrace)\s*[:\n]\s*(.{10,500})", re.IGNORECASE | re.DOTALL),
        re.compile(r"(?:TypeError|ValueError|KeyError|IndexError|AttributeError|RuntimeError|AssertionError)\s*[:\-]?\s*(.{5,300})", re.IGNORECASE),
        re.compile(r"(?:mypy error|tsc error|eslint error|lint error|clippy error)\s*[:\-]?\s*(.{5,300})", re.IGNORECASE),
        re.compile(r"(?:\b\w+Error\b|\b\w+Exception\b)\s*[:\-]?\s*(.{5,300})", re.IGNORECASE),
    ]

    # Stack trace detection
    STACK_TRACE_PATTERN = re.compile(
        r"(Traceback \(most recent call last\):.*?\n(?:  File .+\n(?:    .+\n)*)*(?:\w+Error:.*?\n?.*?)(?=\n\n|\n[A-Z]|\Z))",
        re.DOTALL | re.IGNORECASE,
    )

    def extract(self, text: str) -> List[str]:
        """Extract error statements from session text."""
        errors = []

        # First, extract full stack traces
        for match in self.STACK_TRACE_PATTERN.finditer(text):
            trace = match.group(1).strip()
            if trace:
                errors.append(trace[:500])

        # Then extract pattern-based errors
        for pattern in self.ERROR_PATTERNS:
            for match in pattern.finditer(text):
                error = match.group(1).strip()
                if len(error) < 5:
                    continue
                error = re.sub(r"[.!?;,]+$", "", error)
                errors.append(error)

        # Deduplicate
        seen = set()
        unique = []
        for e in errors:
            key = e.lower()[:80]
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique[:5]
