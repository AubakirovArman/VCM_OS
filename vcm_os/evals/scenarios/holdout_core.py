from vcm_os.evals.scenarios.types import EvalScenario, _evt

def stale_migration_scenario() -> EvalScenario:
    pid = "proj_holdout_01"
    sid = "sess_h01_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: migrate from MySQL to PostgreSQL."),
        _evt(pid, sid, "code_change", "Created PostgreSQL schema.", {"file_path": "db/schema.sql"}),
        _evt(pid, sid, "error", "Migration failed: foreign key constraints violated.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: actually, keep MySQL. PostgreSQL migration is too risky."),
        _evt(pid, sid, "code_change", "Reverted to MySQL.", {"file_path": "db/schema.sql"}),
    ]
    return EvalScenario(
        name="holdout_stale_migration",
        project_id=pid,
        events=events,
        expected_goals=["keep MySQL"],
        expected_decisions=["keep MySQL"],
        expected_errors=["Migration failed"],
        stale_facts=["migrate from MySQL to PostgreSQL"],
        test_query="What database should we use?",
        expected_answer_keywords=["MySQL", "too risky"],
        critical_gold=["MySQL"],
        protected_terms=["PostgreSQL", "MySQL", "db/schema.sql"],
        locked=True,
    )


def exact_env_var_scenario() -> EvalScenario:
    pid = "proj_holdout_02"
    sid = "sess_h02_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: set DATABASE_URL=postgres://prod:5432/app."),
        _evt(pid, sid, "code_change", "Updated .env.production.", {"file_path": ".env.production"}),
        _evt(pid, sid, "user_message", "Decision: REDIS_URL must be redis://cache:6379/0."),
        _evt(pid, sid, "code_change", "Updated .env.production.", {"file_path": ".env.production"}),
        _evt(pid, sid, "user_message", "Decision: STRIPE_SECRET_KEY starts with sk_live_."),
    ]
    return EvalScenario(
        name="holdout_exact_env_var",
        project_id=pid,
        events=events,
        expected_goals=["production config"],
        expected_decisions=["set DATABASE_URL"],
        expected_errors=[],
        test_query="What is the production database URL?",
        expected_answer_keywords=["DATABASE_URL", "postgres://prod:5432/app"],
        critical_gold=["DATABASE_URL"],
        protected_terms=["DATABASE_URL", "REDIS_URL", "STRIPE_SECRET_KEY", ".env.production"],
        locked=True,
    )


def superseded_cache_scenario() -> EvalScenario:
    pid = "proj_holdout_03"
    sid = "sess_h03_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: use Redis for caching. Fast and simple."),
        _evt(pid, sid, "code_change", "Added Redis cache client.", {"file_path": "src/cache/redis.py"}),
        _evt(pid, sid, "error", "Redis memory usage spiked to 90%. Eviction policy losing hot keys.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: switch to Memcached. Better memory management."),
        _evt(pid, sid, "code_change", "Replaced Redis with Memcached.", {"file_path": "src/cache/memcached.py"}),
    ]
    return EvalScenario(
        name="holdout_superseded_cache",
        project_id=pid,
        events=events,
        expected_goals=["switch to Memcached"],
        expected_decisions=["switch to Memcached"],
        expected_errors=["Redis memory usage spiked"],
        stale_facts=["use Redis for caching"],
        test_query="What cache should we use?",
        expected_answer_keywords=["Memcached", "memory management"],
        critical_gold=["Memcached"],
        protected_terms=["Redis", "Memcached", "src/cache/redis.py", "src/cache/memcached.py"],
        locked=True,
    )


def exact_function_name_scenario() -> EvalScenario:
    pid = "proj_holdout_04"
    sid = "sess_h04_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: rename processPayment() to processPaymentV2() for idempotency."),
        _evt(pid, sid, "code_change", "Renamed processPayment to processPaymentV2.", {"file_path": "src/payment/core.ts"}),
        _evt(pid, sid, "user_message", "Decision: validateInput() must check XSS before processing."),
        _evt(pid, sid, "code_change", "Added XSS check in validateInput.", {"file_path": "src/utils/validation.ts"}),
    ]
    return EvalScenario(
        name="holdout_exact_function_name",
        project_id=pid,
        events=events,
        expected_goals=["idempotent payments"],
        expected_decisions=["rename processPayment() to processPaymentV2()"],
        expected_errors=[],
        test_query="What is the payment processing function called?",
        expected_answer_keywords=["processPaymentV2()"],
        critical_gold=["processPaymentV2()"],
        protected_terms=["processPaymentV2()", "validateInput()", "src/payment/core.ts", "src/utils/validation.ts"],
        locked=True,
    )


def multi_session_auth_scenario() -> EvalScenario:
    pid = "proj_holdout_05"
    sid1 = "sess_h05_001"
    sid2 = "sess_h05_002"
    events = [
        _evt(pid, sid1, "user_message", "Decision: use JWT with 15min expiry."),
        _evt(pid, sid1, "code_change", "Added JWT middleware.", {"file_path": "src/auth/jwt.py"}),
        _evt(pid, sid2, "user_message", "Decision: add refresh token rotation."),
        _evt(pid, sid2, "code_change", "Implemented refresh token rotation.", {"file_path": "src/auth/refresh.py"}),
        _evt(pid, sid2, "error", "Refresh token reuse detected: possible theft.", {"error_kind": "security"}),
    ]
    return EvalScenario(
        name="holdout_multi_session_auth",
        project_id=pid,
        events=events,
        expected_goals=["secure auth"],
        expected_decisions=["use JWT with 15min expiry", "add refresh token rotation"],
        expected_errors=["Refresh token reuse detected"],
        test_query="What auth decisions were made across sessions?",
        expected_answer_keywords=["JWT", "15min expiry", "refresh token rotation"],
        critical_gold=["JWT", "refresh token rotation"],
        protected_terms=["src/auth/jwt.py", "src/auth/refresh.py"],
        locked=True,
    )


