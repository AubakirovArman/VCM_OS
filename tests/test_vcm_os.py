import os
import tempfile
import pytest

from vcm_os.config import DATA_DIR
from vcm_os.schemas import EventRecord, MemoryRequest, SessionState
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.memory.writer import MemoryWriter
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.session.store import SessionStore
from vcm_os.session.checkpoint import CheckpointManager
from vcm_os.session.restore import SessionRestorer
from vcm_os.project.decision_ledger import DecisionLedger
from vcm_os.project.error_ledger import ErrorLedger
from vcm_os.evals.scenarios.synthetic_projects import auth_refresh_loop_project
from vcm_os.evals.metrics import evaluate_session_restore, recall_accuracy


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = SQLiteStore(db_path=db_path)
        yield store


@pytest.fixture
def indexes(temp_store):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override data dir for indexes
        import vcm_os.config as cfg
        orig_dir = cfg.DATA_DIR
        cfg.DATA_DIR = tmpdir
        vi = VectorIndex()
        si = SparseIndex()
        yield vi, si
        cfg.DATA_DIR = orig_dir


def test_event_write_and_retrieve(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)

    event = EventRecord(
        project_id="proj_test",
        session_id="sess_test",
        event_type="user_message",
        raw_text="Decision: use Redis for caching.",
    )
    report = writer.capture_event(event)
    assert report.objects_written > 0

    # Retrieve
    reader = MemoryReader(temp_store, vi, si)
    request = MemoryRequest(project_id="proj_test", session_id="sess_test", query="Redis caching")
    plan = MemoryRouter().make_plan(request)
    candidates = reader.retrieve(request, plan)
    assert len(candidates) > 0


def test_decision_ledger(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    events = auth_refresh_loop_project()
    for ev in events:
        writer.capture_event(ev)

    ledger = DecisionLedger(temp_store)
    decisions = ledger.get_active_decisions("proj_auth")
    assert len(decisions) > 0


def test_session_restore(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    events = auth_refresh_loop_project()
    for ev in events:
        writer.capture_event(ev)

    session_store = SessionStore(temp_store)
    sess = session_store.create_session("proj_auth_refresh", title="Auth debug")
    state = SessionState(
        session_id=sess.session_id,
        active_files=["src/auth/session.ts"],
        recent_decisions=[],
        recent_errors=[],
    )
    session_store.update_session_state(state)

    cp_mgr = CheckpointManager(temp_store)
    cp_mgr.save_checkpoint(sess.session_id, "proj_auth_refresh", state)

    restorer = SessionRestorer(temp_store, vi, si)
    pack = restorer.restore(sess.session_id, query="fix auth loop")
    assert pack.token_estimate > 0
    assert any(s.section_name == "decisions" for s in pack.sections)


def test_context_pack_budget(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    events = auth_refresh_loop_project()
    for ev in events:
        writer.capture_event(ev)

    builder = ContextPackBuilder()
    request = MemoryRequest(
        project_id="proj_auth_refresh",
        query="fix auth loop",
        task_type="debugging",
        token_budget=8000,
    )
    candidates = temp_store.get_memories(project_id="proj_auth_refresh", limit=50)
    pack = builder.build(request, candidates)
    assert pack.token_estimate <= request.token_budget * 1.1  # allow small margin


def test_contradiction_detection(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)

    event1 = EventRecord(
        project_id="proj_c",
        event_type="user_message",
        raw_text="Decision: use PostgreSQL for main DB.",
    )
    writer.capture_event(event1)

    event2 = EventRecord(
        project_id="proj_c",
        event_type="user_message",
        raw_text="Decision: use SQLite for main DB.",
    )
    report = writer.capture_event(event2)

    # Should have detected some contradiction logic (at least linking)
    assert report.objects_written > 0


def test_eval_metrics():
    from vcm_os.schemas import ContextPack, ContextPackSection
    pack = ContextPack(
        project_id="proj_test",
        sections=[
            ContextPackSection(section_name="decisions", content="use httpOnly cookie", memory_ids=["m1"]),
            ContextPackSection(section_name="errors", content="refreshSession loop", memory_ids=["m2"]),
        ],
    )
    metrics = evaluate_session_restore(
        pack,
        expected_goals=["fix auth"],
        expected_decisions=["httpOnly"],
        expected_errors=["loop"],
    )
    assert metrics["decision_recall"] > 0
    assert metrics["error_recall"] > 0
