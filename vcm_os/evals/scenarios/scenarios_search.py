from vcm_os.evals.scenarios.types import EvalScenario, _evt

def search_optimization_scenario() -> EvalScenario:
    pid = 'proj_search'
    sid = 'sess_search_001'
    events = [
        _evt(pid, sid, 'user_message', 'Search is too slow. Average 2.5s for product search. Must be <200ms.'),
        _evt(pid, sid, 'assistant_response', 'Will add Elasticsearch and denormalize product data.'),
        _evt(pid, sid, 'code_change', 'Added Elasticsearch index.', {"file_path": "src/search/elastic.py"}),
        _evt(pid, sid, 'error', 'Index out of sync: deleted products still appearing in search.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use CDC with Debezium from PostgreSQL to Elasticsearch.'),
        _evt(pid, sid, 'code_change', 'Added Debezium CDC connector.', {"file_path": "src/search/cdc.py"}),
        _evt(pid, sid, 'tool_call', 'Search latency p95: 45ms.', {"tool_name": "kibana"}),
    ]
    return EvalScenario(
        name='search_optimization',
        project_id=pid,
        events=events,
        expected_goals=['search <200ms'],
        expected_decisions=['use CDC'],
        expected_errors=['index out of sync'],
        test_query='Debezium',
        expected_answer_keywords=['How is search index kept in sync?', 'CDC'],
    )

def search_optimization_regression_scenario() -> EvalScenario:
    pid = 'proj_search_reg'
    sid = 'sess_search_reg_001'
    events = [
        _evt(pid, sid, 'user_message', 'Search is too slow. Average 2.5s for product search. Must be <200ms.'),
        _evt(pid, sid, 'assistant_response', 'Will add Elasticsearch and denormalize product data.'),
        _evt(pid, sid, 'code_change', 'Added Elasticsearch index.', {"file_path": "src/search/elastic.py"}),
        _evt(pid, sid, 'error', 'Index out of sync: deleted products still appearing in search.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: use CDC from PostgreSQL to Elasticsearch.'),
        _evt(pid, sid, 'code_change', 'Added Debezium CDC connector.', {"file_path": "src/search/cdc.py"}),
        _evt(pid, sid, 'tool_call', 'Search latency p95: 45ms.', {"tool_name": "kibana"}),
    ]
    return EvalScenario(
        name='search_optimization_regression',
        project_id=pid,
        events=events,
        expected_goals=['search <200ms'],
        expected_decisions=['use CDC'],
        expected_errors=['index out of sync'],
        test_query='Debezium',
        expected_answer_keywords=['How is search index kept in sync?', 'CDC'],
        critical_gold=['Debezium'],
    )

def background_job_queue_scenario() -> EvalScenario:
    pid = 'proj_queue'
    sid = 'sess_queue_001'
    events = [
        _evt(pid, sid, 'user_message', 'Migrate from Celery to Temporal for background jobs. Need durable execution.'),
        _evt(pid, sid, 'assistant_response', 'Will model each job as Temporal workflow with retries.'),
        _evt(pid, sid, 'code_change', 'Added Temporal workflow for email sending.', {"file_path": "src/workflows/email.py"}),
        _evt(pid, sid, 'error', 'Duplicate emails sent: workflow replay not idempotent.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: all workflows must be idempotent. Use idempotency keys.'),
        _evt(pid, sid, 'code_change', 'Added idempotency key check.', {"file_path": "src/workflows/email.py"}),
    ]
    return EvalScenario(
        name='job_queue_migration',
        project_id=pid,
        events=events,
        expected_goals=['Celery to Temporal'],
        expected_decisions=['all workflows must be idempotent'],
        expected_errors=['duplicate emails'],
        test_query='idempotency keys',
        expected_answer_keywords=['How do we ensure workflow idempotency?', 'idempotent'],
    )

def multi_tenancy_scenario() -> EvalScenario:
    pid = 'proj_tenant'
    sid = 'sess_tenant_001'
    events = [
        _evt(pid, sid, 'user_message', 'Add multi-tenancy. Each tenant isolated. Shared database with tenant_id column.'),
        _evt(pid, sid, 'assistant_response', 'Will add tenant middleware and scoped queries.'),
        _evt(pid, sid, 'code_change', 'Added tenant middleware.', {"file_path": "src/tenant/middleware.py"}),
        _evt(pid, sid, 'error', 'Tenant A seeing Tenant B data: missing tenant filter in admin query.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: ALL queries must include tenant_id. Use query builder that enforces this.'),
        _evt(pid, sid, 'code_change', 'Added mandatory tenant_id filter to query builder.', {"file_path": "src/db/builder.py"}),
        _evt(pid, sid, 'user_message', 'Decision: tenant_id must be set in request context. Fail if missing.'),
    ]
    return EvalScenario(
        name='multi_tenancy',
        project_id=pid,
        events=events,
        expected_goals=['multi-tenancy'],
        expected_decisions=['ALL queries must include tenant_id', 'tenant_id must be set in request context'],
        expected_errors=['tenant A seeing tenant B'],
        test_query='query builder',
        expected_answer_keywords=['How is tenant isolation enforced?', 'tenant_id'],
    )

def config_management_scenario() -> EvalScenario:
    pid = 'proj_config'
    sid = 'sess_config_001'
    events = [
        _evt(pid, sid, 'user_message', 'Move config from env vars to centralized config service. Must support hot reload.'),
        _evt(pid, sid, 'assistant_response', 'Using Consul for config storage with watch mechanism.'),
        _evt(pid, sid, 'code_change', 'Added Consul config client.', {"file_path": "src/config/consul.py"}),
        _evt(pid, sid, 'error', 'Config not reloading: watches timing out during network partition.', {"error_kind": "runtime_error"}),
        _evt(pid, sid, 'user_message', 'Decision: fallback to local config file if Consul unavailable for >30s.'),
        _evt(pid, sid, 'code_change', 'Added local fallback with 30s timeout.', {"file_path": "src/config/fallback.py"}),
    ]
    return EvalScenario(
        name='config_management',
        project_id=pid,
        events=events,
        expected_goals=['centralized config'],
        expected_decisions=['fallback to local config file'],
        expected_errors=['not reloading'],
        test_query='30s',
        expected_answer_keywords=['What happens when Consul is down?', 'fallback'],
    )

