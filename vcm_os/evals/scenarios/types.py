import hashlib
from typing import Dict, List, Optional, Tuple

from vcm_os.schemas import EventRecord


class EvalScenario:
    def __init__(
        self,
        name: str,
        project_id: str,
        events: List[EventRecord],
        expected_goals: List[str],
        expected_decisions: List[str],
        expected_errors: List[str],
        stale_facts: List[str] = None,
        test_query: str = "",
        expected_answer_keywords: List[str] = None,
        critical_gold: List[str] = None,
        protected_terms: List[str] = None,
        expected_rationales: List[str] = None,
        locked: bool = False,
    ):
        self.name = name
        self.project_id = project_id
        self.events = events
        self.expected_goals = expected_goals
        self.expected_decisions = expected_decisions
        self.expected_errors = expected_errors
        self.stale_facts = stale_facts or []
        self.test_query = test_query
        self.expected_answer_keywords = expected_answer_keywords or []
        self.critical_gold = critical_gold or []
        self.protected_terms = protected_terms or []
        self.expected_rationales = expected_rationales or []
        self.locked = locked


def _evt(project_id, session_id, event_type, raw_text, payload=None):
    # Use deterministic hash so event_id is stable across Python runs
    text_hash = hashlib.md5(raw_text.encode("utf-8")).hexdigest()[:8]
    return EventRecord(
        event_id=f"evt_{project_id}_{session_id}_{event_type}_{text_hash}",
        project_id=project_id,
        session_id=session_id,
        event_type=event_type,
        raw_text=raw_text,
        payload=payload or {},
    )
