from typing import Dict, List

from vcm_os.schemas import EventRecord, MemoryRequest
from vcm_os.memory.writer import MemoryWriter
from vcm_os.session.restore import SessionRestorer
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.evals.metrics import evaluate_session_restore, recall_accuracy, token_usage


class EvalHarness:
    def __init__(self, writer: MemoryWriter, restorer: SessionRestorer, pack_builder: ContextPackBuilder):
        self.writer = writer
        self.restorer = restorer
        self.pack_builder = pack_builder

    def run_all(self) -> Dict[str, Dict]:
        scenarios = load_all_scenarios()
        results = {}
        for name, events in scenarios.items():
            results[name] = self._run_scenario(name, events)
        return results

    def _run_scenario(self, name: str, events: List[EventRecord]) -> Dict:
        # Write all events
        for ev in events:
            self.writer.capture_event(ev)

        # Pick last session
        session_id = events[-1].session_id
        project_id = events[-1].project_id

        # Restore session
        pack = self.restorer.restore(session_id, query="Continue fixing the auth refresh loop")

        # Evaluate
        expected_goals = ["fix auth refresh", "offline"]
        expected_decisions = ["httpOnly cookie", "middleware must not refresh"]
        expected_errors = ["test failure", "refreshSession"]

        restore_metrics = evaluate_session_restore(pack, expected_goals, expected_decisions, expected_errors)
        tokens = token_usage(pack)

        return {
            "restore_metrics": restore_metrics,
            "token_usage": tokens,
            "pack": pack.model_dump(),
        }
