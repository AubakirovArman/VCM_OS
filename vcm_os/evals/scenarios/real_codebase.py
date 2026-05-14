"""Real codebase eval scenarios for v0.6.

These scenarios use actual VCM-OS development sessions as the codebase.
The goal is to prove VCM can remember decisions across real dev sessions.
"""

from vcm_os.evals.scenarios.synthetic_projects import EvalScenario, _evt


def vcm_os_dev_session_1_scenario() -> EvalScenario:
    """Real session: Adding rare-term rescue to pack builder."""
    pid = "proj_vcm_os"
    sid = "sess_vcm_dev_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: add rare-term rescue pass to pack builder for missing protected keywords."),
        _evt(pid, sid, "code_change", "Added rescue_protected_terms logic to build() in pack_builder.py.", {"file_path": "vcm_os/context/pack_builder.py"}),
        _evt(pid, sid, "error", "TypeError: unhashable type 'list' in trace.py dedup section.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: fix trace.py seen_ids_flat by iterating memory_ids instead of set()."),
        _evt(pid, sid, "code_change", "Fixed seen_ids_flat construction in trace.py.", {"file_path": "vcm_os/cli/trace.py"}),
    ]
    return EvalScenario(
        name="vcm_os_dev_session_1",
        project_id=pid,
        events=events,
        expected_goals=["rare-term rescue pass"],
        expected_decisions=["add rare-term rescue pass to pack builder", "fix trace.py seen_ids_flat"],
        expected_errors=["TypeError: unhashable type 'list'"],
        test_query="What was added to the pack builder for missing keywords?",
        expected_answer_keywords=["rare-term rescue", "protected keywords", "pack builder"],
        critical_gold=["rare-term rescue pass"],
        protected_terms=["pack_builder.py", "trace.py", "TypeError"],
        locked=True,
    )


def vcm_os_dev_session_2_scenario() -> EvalScenario:
    """Real session: Fixing duplicate requirements root cause."""
    pid = "proj_vcm_os"
    sid = "sess_vcm_dev_002"
    events = [
        _evt(pid, sid, "user_message", "Decision: use deterministic md5 hash for event_id in synthetic_projects.py instead of Python hash()."),
        _evt(pid, sid, "code_change", "Replaced hash(raw_text) % 10000 with hashlib.md5(raw_text.encode()).hexdigest()[:8].", {"file_path": "vcm_os/evals/scenarios/synthetic_projects.py"}),
        _evt(pid, sid, "tool_call", "Diagnose shows 10 memories after cleanup, 0 unexplained duplicates.", {"tool_name": "diagnose"}),
        _evt(pid, sid, "user_message", "Decision: canonicalization key must use sha256(normalized_raw_text).hexdigest(), not truncated raw_text[:120]."),
        _evt(pid, sid, "code_change", "Updated writer.py canonical key to full SHA256 hash.", {"file_path": "vcm_os/memory/writer.py"}),
    ]
    return EvalScenario(
        name="vcm_os_dev_session_2",
        project_id=pid,
        events=events,
        expected_goals=["duplicate requirements bug fixed"],
        expected_decisions=["use deterministic md5 hash for event_id", "canonicalization key must use sha256"],
        expected_errors=[],
        test_query="How was the duplicate requirements bug fixed?",
        expected_answer_keywords=["md5", "deterministic", "sha256", "canonicalization"],
        critical_gold=["md5", "sha256"],
        protected_terms=["synthetic_projects.py", "writer.py", "hashlib"],
        locked=True,
    )


def vcm_os_dev_session_3_scenario() -> EvalScenario:
    """Real session: Building adversarial exact-symbol benchmark."""
    pid = "proj_vcm_os"
    sid = "sess_vcm_dev_003"
    events = [
        _evt(pid, sid, "user_message", "Decision: create adversarial exact-symbol scenarios with sibling terms that vector confuses."),
        _evt(pid, sid, "code_change", "Created adversarial_symbols.py with FEATURE_AUTH_REFRESH_V2/V3/LEGACY/STAGING/PROD.", {"file_path": "vcm_os/evals/scenarios/adversarial_symbols.py"}),
        _evt(pid, sid, "tool_call", "Adversarial F03: hybrid beats vector-only by +0.333 to +0.667 on exact symbols.", {"tool_name": "eval"}),
        _evt(pid, sid, "user_message", "Decision: add protected_evidence rescue section to pack builder with 30-token budget."),
    ]
    return EvalScenario(
        name="vcm_os_dev_session_3",
        project_id=pid,
        events=events,
        expected_goals=["adversarial exact-symbol benchmark"],
        expected_decisions=["create adversarial exact-symbol scenarios", "add protected_evidence rescue section"],
        expected_errors=[],
        test_query="What benchmark was created for exact-symbol retrieval?",
        expected_answer_keywords=["adversarial", "exact-symbol", "FEATURE_AUTH_REFRESH_V2"],
        critical_gold=["adversarial", "exact-symbol"],
        protected_terms=["adversarial_symbols.py", "FEATURE_AUTH_REFRESH_V2"],
        locked=True,
    )


def load_real_codebase_scenarios():
    return [
        vcm_os_dev_session_1_scenario(),
        vcm_os_dev_session_2_scenario(),
        vcm_os_dev_session_3_scenario(),
    ]
