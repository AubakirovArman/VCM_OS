from typing import Tuple

from vcm_os.evals.scenarios.types import EvalScenario, _evt

def false_memory_s05() -> EvalScenario:
    pid = 'proj_false'
    sid = 'sess_false_001'
    events = [
        _evt(pid, sid, 'user_message', 'What is our primary database?'),
        _evt(pid, sid, 'assistant_response', 'We use PostgreSQL with read replicas. This was decided last month.'),
        _evt(pid, sid, 'user_message', 'Actually we never decided that. We use SQLite.'),
        _evt(pid, sid, 'user_message', 'Decision: primary DB is SQLite. No replicas needed.'),
    ]
    return EvalScenario(
        name='false_memory_s05',
        project_id=pid,
        events=events,
        expected_goals=['correct database choice'],
        expected_decisions=['SQLite'],
        expected_errors=[],
        test_query='SQLite',
        expected_answer_keywords=['What is our primary database?'],
    )

def project_switching_h03() -> Tuple[EvalScenario, EvalScenario, EvalScenario]:
    a = EvalScenario(
        name="h03_project_A",
        project_id="proj_switch_A",
        events=[
            _evt("proj_switch_A", "sess_a_001", "user_message", "Project A: Use PostgreSQL with read replicas."),
            _evt("proj_switch_A", "sess_a_001", "code_change", "Added PostgreSQL config.", {"file_path": "src/db/postgres.py"}),
        ],
        expected_goals=["use PostgreSQL"],
        expected_decisions=["PostgreSQL with read replicas"],
        expected_errors=[],
        test_query="What database does Project A use?",
        expected_answer_keywords=["PostgreSQL"],
    )
    b = EvalScenario(
        name="h03_project_B",
        project_id="proj_switch_B",
        events=[
            _evt("proj_switch_B", "sess_b_001", "user_message", "Project B: Use SQLite for simplicity."),
            _evt("proj_switch_B", "sess_b_001", "code_change", "Added SQLite config.", {"file_path": "src/db/sqlite.py"}),
        ],
        expected_goals=["use SQLite"],
        expected_decisions=["SQLite for simplicity"],
        expected_errors=[],
        test_query="What database does Project B use?",
        expected_answer_keywords=["SQLite"],
    )
    c = EvalScenario(
        name="h03_project_C",
        project_id="proj_switch_C",
        events=[
            _evt("proj_switch_C", "sess_c_001", "user_message", "Project C: Use MongoDB for flexibility."),
            _evt("proj_switch_C", "sess_c_001", "code_change", "Added MongoDB config.", {"file_path": "src/db/mongo.py"}),
        ],
        expected_goals=["use MongoDB"],
        expected_decisions=["MongoDB for flexibility"],
        expected_errors=[],
        test_query="What database does Project C use?",
        expected_answer_keywords=["MongoDB"],
    )
    return a, b, c

def superseded_decision_scenario() -> EvalScenario:
    pid = 'proj_super'
    sid = 'sess_super_001'
    events = [
        _evt(pid, sid, 'user_message', "Decision: use Redis for session store. It's fast and simple."),
        _evt(pid, sid, 'code_change', 'Added Redis client to src/auth/session.ts', {"file_path": "src/auth/session.ts"}),
        _evt(pid, sid, 'error', 'Redis connection timeout under load: 500ms latency on session reads.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: switch to Memcached for session store. Redis caused unacceptable latency under load.'),
        _evt(pid, sid, 'code_change', 'Replaced Redis with Memcached in src/auth/session.ts', {"file_path": "src/auth/session.ts"}),
        _evt(pid, sid, 'tool_call', 'Load test passed: session reads < 10ms with Memcached', {"tool_name": "k6"}),
    ]
    return EvalScenario(
        name='superseded_decision',
        project_id=pid,
        events=events,
        expected_goals=['switch to Memcached for session store'],
        expected_decisions=['switch to Memcached for session store', 'Redis caused unacceptable latency'],
        expected_errors=['Redis connection timeout under load'],
        test_query='What is the current session store decision?',
        expected_answer_keywords=['use Redis for session store'],
    )

