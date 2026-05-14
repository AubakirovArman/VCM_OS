"""Realistic multi-repo scenarios.

These scenarios mimic actual development across distinct repositories
with realistic file paths, commit messages, and error logs.
"""

from typing import List
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario, _evt


def repo_fastapi_auth() -> EvalScenario:
    pid = "repo_fastapi_auth"
    sid = "sess_fa_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: use OAuth2 with PasswordBearer for FastAPI auth. Token URL is /token."),
        _evt(pid, sid, "code_change", "Created auth router with OAuth2PasswordBearer(tokenUrl='/token').", {"file_path": "app/routers/auth.py"}),
        _evt(pid, sid, "error", "RuntimeError: SECRET_KEY not set in environment. Application refuses to start.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "code_change", "Added SECRET_KEY validation in config.py with fallback to .env.", {"file_path": "app/core/config.py"}),
        _evt(pid, sid, "user_message", "Decision: token expiry 30 minutes, refresh token 7 days. Store refresh tokens in Redis."),
        _evt(pid, sid, "code_change", "Implemented refresh token rotation with Redis backend.", {"file_path": "app/services/auth.py"}),
    ]
    return EvalScenario(
        name="repo_fastapi_auth",
        project_id=pid,
        events=events,
        expected_goals=["secure FastAPI auth"],
        expected_decisions=["use OAuth2 with PasswordBearer", "token expiry 30 minutes"],
        expected_errors=["SECRET_KEY not set"],
        test_query="What is the FastAPI auth setup?",
        expected_answer_keywords=["OAuth2", "PasswordBearer", "/token", "30 minutes", "Redis"],
        critical_gold=["OAuth2", "PasswordBearer"],
        protected_terms=["app/routers/auth.py", "app/core/config.py", "app/services/auth.py"],
        locked=True,
    )


def repo_cli_tool_config() -> EvalScenario:
    pid = "repo_cli_tool_config"
    sid = "sess_cli_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: CLI config in TOML, not YAML. PyPI package name: vcm-cli."),
        _evt(pid, sid, "code_change", "Created pyproject.toml with [tool.vcm-cli] section.", {"file_path": "pyproject.toml"}),
        _evt(pid, sid, "error", "toml.TomlDecodeError: Invalid escape sequence in config file on Windows paths.", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: use raw strings for Windows paths in TOML. Add path validation."),
        _evt(pid, sid, "code_change", "Added pathlib.Path validation and raw string handling.", {"file_path": "vcm_cli/config.py"}),
    ]
    return EvalScenario(
        name="repo_cli_tool_config",
        project_id=pid,
        events=events,
        expected_goals=["robust CLI config"],
        expected_decisions=["TOML not YAML", "raw strings for Windows paths"],
        expected_errors=["TomlDecodeError"],
        test_query="What config format does the CLI use?",
        expected_answer_keywords=["TOML", "raw strings", "Windows paths"],
        critical_gold=["TOML"],
        protected_terms=["pyproject.toml", "vcm_cli/config.py", "TomlDecodeError"],
        locked=True,
    )


def repo_data_pipeline() -> EvalScenario:
    pid = "repo_data_pipeline"
    sid = "sess_dp_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: use Polars instead of Pandas for ETL. Memory usage is 10x lower."),
        _evt(pid, sid, "code_change", "Replaced pd.read_csv with pl.read_csv in pipeline.", {"file_path": "etl/extract.py"}),
        _evt(pid, sid, "error", "Polars SchemaError: column 'user_id' has mixed types (int and string).", {"error_kind": "runtime_error"}),
        _evt(pid, sid, "user_message", "Decision: enforce string type for user_id during extraction. Cast all IDs to str."),
        _evt(pid, sid, "code_change", "Added .cast(pl.Utf8) for user_id column.", {"file_path": "etl/extract.py"}),
        _evt(pid, sid, "tool_call", "ETL benchmark: 1M rows in 2.3s vs 18s with Pandas.", {"tool_name": "benchmark"}),
    ]
    return EvalScenario(
        name="repo_data_pipeline",
        project_id=pid,
        events=events,
        expected_goals=["fast ETL pipeline"],
        expected_decisions=["use Polars instead of Pandas", "enforce string type for user_id"],
        expected_errors=["SchemaError"],
        test_query="Why did we switch from Pandas to Polars?",
        expected_answer_keywords=["Polars", "memory usage", "10x lower", "2.3s"],
        critical_gold=["Polars"],
        protected_terms=["etl/extract.py", "Polars", "SchemaError"],
        locked=True,
    )


def repo_docker_deploy() -> EvalScenario:
    pid = "repo_docker_deploy"
    sid = "sess_dd_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: multi-stage Docker build. Final image based on distroless python3.11."),
        _evt(pid, sid, "code_change", "Created Dockerfile with builder and runtime stages.", {"file_path": "Dockerfile"}),
        _evt(pid, sid, "error", "Build failed: gcc not found in distroless image. Need compile deps in builder.", {"error_kind": "build_failure"}),
        _evt(pid, sid, "code_change", "Added apt-get install gcc in builder stage, copied .so files.", {"file_path": "Dockerfile"}),
        _evt(pid, sid, "user_message", "Decision: use BuildKit cache mounts for pip to speed up CI."),
        _evt(pid, sid, "code_change", "Added --mount=type=cache,target=/root/.cache/pip.", {"file_path": "Dockerfile"}),
    ]
    return EvalScenario(
        name="repo_docker_deploy",
        project_id=pid,
        events=events,
        expected_goals=["optimized Docker build"],
        expected_decisions=["multi-stage Docker build", "distroless python3.11", "BuildKit cache mounts"],
        expected_errors=["gcc not found"],
        test_query="What is the Docker base image?",
        expected_answer_keywords=["distroless", "python3.11", "multi-stage"],
        critical_gold=["distroless"],
        protected_terms=["Dockerfile", "distroless", "BuildKit"],
        locked=True,
    )


def repo_testing_pytest() -> EvalScenario:
    pid = "repo_testing_pytest"
    sid = "sess_pt_001"
    events = [
        _evt(pid, sid, "user_message", "Decision: pytest with xdist for parallel tests. 4 workers in CI."),
        _evt(pid, sid, "code_change", "Added pytest-xdist to dev deps and -n 4 to CI config.", {"file_path": ".github/workflows/test.yml"}),
        _evt(pid, sid, "error", "Flaky test: test_concurrent_write fails when run in parallel. Race condition in temp file.", {"error_kind": "test_failure"}),
        _evt(pid, sid, "user_message", "Decision: use pytest tmp_path fixture instead of manual temp files."),
        _evt(pid, sid, "code_change", "Replaced manual tempfile with tmp_path fixture.", {"file_path": "tests/test_storage.py"}),
    ]
    return EvalScenario(
        name="repo_testing_pytest",
        project_id=pid,
        events=events,
        expected_goals=["reliable parallel tests"],
        expected_decisions=["pytest with xdist", "tmp_path fixture"],
        expected_errors=["Flaky test", "Race condition"],
        test_query="How did we fix the flaky concurrent write test?",
        expected_answer_keywords=["tmp_path", "fixture", "tempfile"],
        critical_gold=["tmp_path"],
        protected_terms=[".github/workflows/test.yml", "tests/test_storage.py", "pytest-xdist"],
        locked=True,
    )


def load_realistic_multi_repo_scenarios() -> List[EvalScenario]:
    return [
        repo_fastapi_auth(),
        repo_cli_tool_config(),
        repo_data_pipeline(),
        repo_docker_deploy(),
        repo_testing_pytest(),
    ]
