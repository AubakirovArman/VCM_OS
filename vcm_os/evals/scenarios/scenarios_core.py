from vcm_os.evals.scenarios.types import EvalScenario, _evt

def auth_refresh_loop_scenario() -> EvalScenario:
    pid = 'proj_auth'
    sid = 'sess_auth_001'
    events = [
        _evt(pid, sid, 'user_message', 'We need to fix the auth refresh token loop. It must work offline and use httpOnly cookies.'),
        _evt(pid, sid, 'assistant_response', "I'll investigate validateSession in src/auth/session.ts. It seems to call refreshSession recursively."),
        _evt(pid, sid, 'code_change', 'Modified validateSession to not call refreshSession in middleware path.', {"file_path": "src/auth/session.ts"}),
        _evt(pid, sid, 'error', 'tests/auth.test.ts still failing: refreshSession called repeatedly.', {"error_kind": "test_failure"}),
        _evt(pid, sid, 'user_message', 'Decision: use httpOnly cookie for refresh token. Rationale: reduces XSS exposure. Middleware must not refresh on every request. Rationale: avoid recursive refresh calls.'),
        _evt(pid, sid, 'code_change', 'Updated middleware to skip refresh during validation. Added explicit refresh on token expiry.', {"file_path": "src/auth/middleware.ts"}),
        _evt(pid, sid, 'tool_call', 'pytest auth suite: 12 passed, 0 failed.', {"tool_name": "pytest"}),
    ]
    return EvalScenario(
        name='auth_refresh_loop',
        project_id=pid,
        events=events,
        expected_goals=['fix auth refresh loop'],
        expected_decisions=['use httpOnly cookie', 'middleware must not refresh'],
        expected_errors=['tests/auth.test.ts still failing'],
        test_query='middleware must not refresh',
        expected_answer_keywords=['How do I fix the auth refresh loop?', 'httpOnly cookie'],
        expected_rationales=['reduces XSS exposure', 'avoid recursive refresh calls'],
    )

def payment_rewrite_scenario() -> EvalScenario:
    pid = 'proj_payment'
    sid = 'sess_payment_001'
    events = [
        _evt(pid, sid, 'user_message', 'Start payment rewrite. Use Stripe and support partial refunds.'),
        _evt(pid, sid, 'assistant_response', 'Will create src/payment/stripe.ts and partial refund logic.'),
        _evt(pid, sid, 'code_change', 'Added Stripe integration and refund endpoint.', {"file_path": "src/payment/stripe.ts"}),
        _evt(pid, sid, 'error', 'Refund test failed: amount must be positive integer.', {"error_kind": "test_failure"}),
        _evt(pid, sid, 'user_message', 'Decision: partial refunds require admin approval above $100.'),
        _evt(pid, sid, 'code_change', 'Added approval gate for refunds > $100.', {"file_path": "src/payment/refund.ts"}),
    ]
    return EvalScenario(
        name='payment_rewrite',
        project_id=pid,
        events=events,
        expected_goals=['payment rewrite'],
        expected_decisions=['partial refunds require admin approval above $100'],
        expected_errors=['refund test failed'],
        test_query='What are the refund rules?',
        expected_answer_keywords=[],
    )

def database_migration_scenario() -> EvalScenario:
    pid = 'proj_db'
    sid = 'sess_db_001'
    events = [
        _evt(pid, sid, 'user_message', 'Migrate from MongoDB to PostgreSQL. Must preserve all user data.'),
        _evt(pid, sid, 'assistant_response', 'Plan: dump MongoDB, transform schema, import to Postgres.'),
        _evt(pid, sid, 'code_change', 'Created migration script v1.', {"file_path": "scripts/migrate_v1.py"}),
        _evt(pid, sid, 'error', 'Migration failed: ObjectId cannot convert to UUID.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: map ObjectId to UUIDv5 with namespace.'),
        _evt(pid, sid, 'code_change', 'Updated migration script v2 with UUID mapping.', {"file_path": "scripts/migrate_v2.py"}),
        _evt(pid, sid, 'tool_call', 'Migration completed: 1.2M users migrated successfully.', {"tool_name": "pytest"}),
        _evt(pid, sid, 'user_message', 'Decision: v1 migration script is deprecated. Use v2 only.'),
    ]
    return EvalScenario(
        name='db_migration',
        project_id=pid,
        events=events,
        expected_goals=['migrate MongoDB to PostgreSQL'],
        expected_decisions=['map ObjectId to UUIDv5', 'v1 migration script is deprecated'],
        expected_errors=['migration failed'],
        test_query='How do we handle ObjectId during migration?',
        expected_answer_keywords=['v1 migration script'],
    )

def api_versioning_scenario() -> EvalScenario:
    pid = 'proj_api'
    sid = 'sess_api_001'
    events = [
        _evt(pid, sid, 'user_message', 'We need API v2 with breaking changes to user profiles. Keep v1 running for 6 months.'),
        _evt(pid, sid, 'assistant_response', 'Will create /v2/users with new schema. v1 stays at /v1/users.'),
        _evt(pid, sid, 'code_change', 'Added v2 user endpoints.', {"file_path": "src/api/v2/users.ts"}),
        _evt(pid, sid, 'error', "v1 clients getting 400 on profile update: missing new 'preferences' field.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: v1 must ignore unknown fields, not reject them.'),
        _evt(pid, sid, 'code_change', 'Updated v1 validator to ignore unknown fields.', {"file_path": "src/api/v1/validator.ts"}),
        _evt(pid, sid, 'user_message', 'Decision: sunset v1 on 2027-01-01. Announce deprecation now.'),
    ]
    return EvalScenario(
        name='api_versioning',
        project_id=pid,
        events=events,
        expected_goals=['API v2 with breaking changes'],
        expected_decisions=['v1 must ignore unknown fields', 'sunset v1 on 2027-01-01'],
        expected_errors=['v1 clients getting 400'],
        test_query='sunset v1',
        expected_answer_keywords=['v1 rejects unknown fields'],
        critical_gold=['What is the v1 sunset policy?', 'v1 must ignore unknown fields'],
    )

def microservices_decomposition_scenario() -> EvalScenario:
    pid = 'proj_micro'
    sid = 'sess_micro_001'
    events = [
        _evt(pid, sid, 'user_message', 'Split monolith into user-service and order-service. Use gRPC internally.'),
        _evt(pid, sid, 'assistant_response', 'Extracting user domain first, then order domain.'),
        _evt(pid, sid, 'code_change', 'Created user-service with gRPC proto.', {"file_path": "services/user/main.py"}),
        _evt(pid, sid, 'error', 'Circular dependency: order-service imports user-service and vice versa.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: shared models go to common-lib. No cross-service imports.'),
        _evt(pid, sid, 'code_change', 'Extracted shared models to common-lib.', {"file_path": "libs/common/models.py"}),
        _evt(pid, sid, 'user_message', 'Decision: use event bus for async communication, not direct gRPC for everything.'),
    ]
    return EvalScenario(
        name='microservices_decomposition',
        project_id=pid,
        events=events,
        expected_goals=['split monolith'],
        expected_decisions=['shared models go to common-lib', 'use event bus for async communication'],
        expected_errors=['circular dependency'],
        test_query='common-lib',
        expected_answer_keywords=['How do services communicate?', 'event bus'],
    )

def cache_invalidation_scenario() -> EvalScenario:
    pid = 'proj_cache'
    sid = 'sess_cache_001'
    events = [
        _evt(pid, sid, 'user_message', 'Cache invalidation is broken. Users see stale data for 5 minutes after updates.'),
        _evt(pid, sid, 'assistant_response', 'Checking Redis TTL and cache keys.'),
        _evt(pid, sid, 'code_change', 'Added cache-bust on user update.', {"file_path": "src/cache/bust.py"}),
        _evt(pid, sid, 'error', 'Cache stampede: 1000 requests hit DB after invalidation.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use cache-aside with probabilistic early expiration.'),
        _evt(pid, sid, 'code_change', 'Implemented probabilistic expiration.', {"file_path": "src/cache/expire.py"}),
    ]
    return EvalScenario(
        name='cache_invalidation',
        project_id=pid,
        events=events,
        expected_goals=['fix cache invalidation'],
        expected_decisions=['use cache-aside with probabilistic early expiration'],
        expected_errors=['cache stampede'],
        test_query='How do we prevent cache stampedes?',
        expected_answer_keywords=[],
    )

def race_condition_scenario() -> EvalScenario:
    pid = 'proj_race'
    sid = 'sess_race_001'
    events = [
        _evt(pid, sid, 'user_message', 'Race condition in inventory allocation. Two orders got last item.'),
        _evt(pid, sid, 'assistant_response', 'Checking database isolation level and locking strategy.'),
        _evt(pid, sid, 'code_change', 'Added pessimistic lock on inventory row.', {"file_path": "src/inventory/lock.py"}),
        _evt(pid, sid, 'error', "Deadlock: two transactions waiting for each other's inventory locks.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use optimistic locking with version column.'),
        _evt(pid, sid, 'code_change', 'Replaced pessimistic lock with optimistic version check.', {"file_path": "src/inventory/allocate.py"}),
    ]
    return EvalScenario(
        name='race_condition',
        project_id=pid,
        events=events,
        expected_goals=['fix race condition'],
        expected_decisions=['use optimistic locking with version column'],
        expected_errors=['deadlock'],
        test_query='version column',
        expected_answer_keywords=['How is inventory allocation handled?', 'optimistic locking'],
    )

