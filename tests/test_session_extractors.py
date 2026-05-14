"""Tests for session goal/error extractors."""
from vcm_os.memory.writer.session_extractors import SessionErrorExtractor, SessionGoalExtractor


def test_goal_extractor_basic():
    ext = SessionGoalExtractor()
    text = "We need to refactor the auth system. Then we should update tests."
    goals = ext.extract(text)
    assert len(goals) == 2
    assert "refactor the auth system" in goals[0]
    assert "update tests" in goals[1]


def test_goal_extractor_patterns():
    ext = SessionGoalExtractor()
    text = (
        "The goal is to improve performance. "
        "Let's fix the memory leak. "
        "Need to implement caching. "
        "Continue from where we left off on the API. "
        "Priority: security audit"
    )
    goals = ext.extract(text)
    assert len(goals) == 5
    assert any("improve performance" in g for g in goals)
    assert any("memory leak" in g for g in goals)
    assert any("caching" in g for g in goals)
    assert any("API" in g for g in goals)
    assert any("security audit" in g for g in goals)


def test_goal_extractor_filters_speculation():
    ext = SessionGoalExtractor()
    text = "I think we should use Redis. We need to add caching."
    goals = ext.extract(text)
    assert len(goals) == 1
    assert "caching" in goals[0]


def test_goal_extractor_dedup():
    ext = SessionGoalExtractor()
    text = "We need to fix auth. And later we need to fix auth again."
    goals = ext.extract(text)
    # Should deduplicate identical goals
    assert len(goals) == 1 or (len(goals) == 2 and goals[0] != goals[1])


def test_error_extractor_basic():
    ext = SessionErrorExtractor()
    text = "Test failed because the mock was not configured. Got an error in line 42."
    errors = ext.extract(text)
    # Multiple patterns may match, but key errors should be present
    assert any("mock was not configured" in e for e in errors)
    assert any("line 42" in e for e in errors)


def test_error_extractor_stack_trace():
    ext = SessionErrorExtractor()
    text = """Traceback (most recent call last):
  File "app.py", line 10, in <module>
    main()
  File "app.py", line 5, in main
    raise ValueError("invalid config")
ValueError: invalid config

Some normal text here."""
    errors = ext.extract(text)
    assert len(errors) >= 1
    assert any("ValueError" in e for e in errors)


def test_error_extractor_type_errors():
    ext = SessionErrorExtractor()
    text = "TypeError: unsupported operand type. mypy error: Missing return type."
    errors = ext.extract(text)
    assert len(errors) == 2
    assert any("unsupported operand" in e for e in errors)
    assert any("Missing return type" in e for e in errors)


def test_error_extractor_dedup():
    ext = SessionErrorExtractor()
    text = "Test failed. Test failed."
    errors = ext.extract(text)
    assert len(errors) == 1
