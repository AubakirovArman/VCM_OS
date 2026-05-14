from vcm_os.evals.scenarios.types import EvalScenario, _evt

def exact_cve_patch_scenario() -> EvalScenario:
    pid = "proj_holdout_06"
    sid = "sess_h06_001"
    events = [
        _evt(pid, sid, "user_message", "Security alert: CVE-2024-9999 affects django<4.2.10."),
        _evt(pid, sid, "assistant_response", "Will upgrade Django and run security audit."),
        _evt(pid, sid, "code_change", "Updated requirements.txt: django>=4.2.10", {"file_path": "requirements.txt"}),
        _evt(pid, sid, "tool_call", "Security scan: no traces of CVE-2024-9999", {"tool_name": "safety"}),
    ]
    return EvalScenario(
        name="holdout_exact_cve_patch",
        project_id=pid,
        events=events,
        expected_goals=["patch CVE-2024-9999"],
        expected_decisions=["upgrade Django"],
        expected_errors=[],
        test_query="What was the patch for CVE-2024-9999?",
        expected_answer_keywords=["CVE-2024-9999", "django>=4.2.10"],
        critical_gold=["CVE-2024-9999"],
        protected_terms=["CVE-2024-9999", "django>=4.2.10", "requirements.txt"],
        locked=True,
    )


def code_change_only_decision_scenario() -> EvalScenario:
    pid = "proj_holdout_07"
    sid = "sess_h07_001"
    events = [
        _evt(pid, sid, "user_message", "We need to handle rate limiting properly."),
        _evt(pid, sid, "code_change", "Added RateLimiter class with token bucket algorithm.", {"file_path": "src/rate/limiter.py"}),
        _evt(pid, sid, "code_change", "Configured 1000 req/min for /api/v1, 100 req/min for /api/v2.", {"file_path": "src/rate/config.py"}),
    ]
    return EvalScenario(
        name="holdout_code_change_only",
        project_id=pid,
        events=events,
        expected_goals=["rate limiting"],
        expected_decisions=["Added RateLimiter class with token bucket algorithm"],
        expected_errors=[],
        test_query="How is rate limiting implemented?",
        expected_answer_keywords=["RateLimiter", "token bucket", "1000 req/min"],
        critical_gold=["RateLimiter"],
        protected_terms=["src/rate/limiter.py", "src/rate/config.py", "token bucket"],
        locked=True,
    )


def error_only_debugging_scenario() -> EvalScenario:
    pid = "proj_holdout_08"
    sid = "sess_h08_001"
    events = [
        _evt(pid, sid, "error", "NullPointerException in UserService.getProfile() at line 142.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "code_change", "Added null check in getProfile.", {"file_path": "src/service/UserService.java"}),
        _evt(pid, sid, "error", "Same NPE in getProfile() after fix. Line 142 still null.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: rewrite getProfile() to use Optional<> instead of null checks."),
    ]
    return EvalScenario(
        name="holdout_error_only_debugging",
        project_id=pid,
        events=events,
        expected_goals=["fix NPE"],
        expected_decisions=["rewrite getProfile() to use Optional<>"],
        expected_errors=["NullPointerException in UserService.getProfile()"],
        test_query="What was the final fix for the NPE in getProfile?",
        expected_answer_keywords=["Optional<>", "getProfile()", "UserService"],
        critical_gold=["Optional<>"],
        protected_terms=["UserService.java", "getProfile()", "NullPointerException"],
        locked=True,
    )


