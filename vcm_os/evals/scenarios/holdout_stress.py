from vcm_os.evals.scenarios.types import EvalScenario, _evt

def long_text_budget_stress_scenario() -> EvalScenario:
    pid = "proj_holdout_09"
    sid = "sess_h09_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: implement full-text search with Elasticsearch. Must support fuzzy matching, synonyms, highlighting, and multi-language analyzers. The index must be sharded across 3 nodes with replication factor 2. Search latency must be under 50ms p95."),
        _evt(pid, sid, "code_change", "Created Elasticsearch index mapping with custom analyzers.", {"file_path": "src/search/mapping.json"}),
        _evt(pid, sid, "error", "Search latency 120ms: too many shards causing overhead.", {"error_kind": "performance"}),
        _evt(pid, sid, "user_message", "Decision: reduce shards to 1 per node. Accept eventual consistency for reads."),
    ]
    return EvalScenario(
        name="holdout_long_text_budget_stress",
        project_id=pid,
        events=events,
        expected_goals=["full-text search under 50ms"],
        expected_decisions=["reduce shards to 1 per node"],
        expected_errors=["Search latency 120ms"],
        test_query="What was the shard configuration decision?",
        expected_answer_keywords=["reduce shards to 1 per node", "eventual consistency"],
        critical_gold=["reduce shards to 1 per node"],
        protected_terms=["src/search/mapping.json", "Elasticsearch", "50ms"],
        locked=True,
    )


def contradiction_same_file_scenario() -> EvalScenario:
    pid = "proj_holdout_10"
    sid = "sess_h10_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: use TypeScript strict mode in tsconfig.json."),
        _evt(pid, sid, "code_change", "Enabled strict: true.", {"file_path": "tsconfig.json"}),
        _evt(pid, sid, "error", "Build broke: 500+ type errors in legacy code.", {"error_kind": "build_failure"}),
        _evt(pid, sid, "user_message", "Decision: disable strict mode. Enable gradually per module."),
        _evt(pid, sid, "code_change", "Set strict: false, added strict per module.", {"file_path": "tsconfig.json"}),
    ]
    return EvalScenario(
        name="holdout_contradiction_same_file",
        project_id=pid,
        events=events,
        expected_goals=["gradual TypeScript strict mode"],
        expected_decisions=["disable strict mode"],
        expected_errors=["Build broke"],
        stale_facts=["use TypeScript strict mode"],
        test_query="What is the TypeScript strict mode configuration?",
        expected_answer_keywords=["disable strict mode", "gradually per module"],
        critical_gold=["disable strict mode"],
        protected_terms=["tsconfig.json", "strict mode"],
        locked=True,
    )


def exact_version_scenario() -> EvalScenario:
    pid = "proj_holdout_11"
    sid = "sess_h11_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: upgrade Node.js to 20.11.0 LTS."),
        _evt(pid, sid, "code_change", "Updated .nvmrc to 20.11.0.", {"file_path": ".nvmrc"}),
        _evt(pid, sid, "user_message", "Decision: pin Python to 3.12.2 for reproducibility."),
        _evt(pid, sid, "code_change", "Updated pyproject.toml python = \"^3.12.2\".", {"file_path": "pyproject.toml"}),
    ]
    return EvalScenario(
        name="holdout_exact_version",
        project_id=pid,
        events=events,
        expected_goals=["version pinning"],
        expected_decisions=["upgrade Node.js to 20.11.0 LTS"],
        expected_errors=[],
        test_query="What Node.js version are we using?",
        expected_answer_keywords=["20.11.0", "LTS"],
        critical_gold=["20.11.0"],
        protected_terms=["20.11.0", "3.12.2", ".nvmrc", "pyproject.toml"],
        locked=True,
    )


def multi_tenant_config_scenario() -> EvalScenario:
    pid = "proj_holdout_12"
    sid = "sess_h12_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: each tenant gets separate PostgreSQL schema."),
        _evt(pid, sid, "code_change", "Added schema routing middleware.", {"file_path": "src/tenant/schema.py"}),
        _evt(pid, sid, "error", "Cross-tenant data leak: schema routing failed on concurrent requests.", {"error_kind": "security"}),
        _evt(pid, sid, "user_message", "Decision: use row-level security instead of schemas."),
        _evt(pid, sid, "code_change", "Implemented RLS policies.", {"file_path": "src/tenant/rls.py"}),
    ]
    return EvalScenario(
        name="holdout_multi_tenant_config",
        project_id=pid,
        events=events,
        expected_goals=["secure multi-tenancy"],
        expected_decisions=["use row-level security instead of schemas"],
        expected_errors=["Cross-tenant data leak"],
        stale_facts=["each tenant gets separate PostgreSQL schema"],
        test_query="How is tenant isolation implemented?",
        expected_answer_keywords=["row-level security", "RLS"],
        critical_gold=["row-level security"],
        protected_terms=["src/tenant/schema.py", "src/tenant/rls.py", "PostgreSQL"],
        locked=True,
    )


