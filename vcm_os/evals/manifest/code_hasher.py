"""Hash Python source files to detect evaluator/runner changes."""
import hashlib
import inspect
from pathlib import Path
from typing import Callable, Optional


def hash_file(path: str) -> str:
    """SHA-256 of file contents."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def hash_module_file(module) -> str:
    """Hash the source file of a loaded module."""
    try:
        path = inspect.getfile(module)
        return hash_file(path)
    except (TypeError, OSError):
        return ""


def hash_callable_source(fn: Callable) -> str:
    """Hash the source code of a function/method."""
    try:
        source = inspect.getsource(fn)
        return hashlib.sha256(source.encode("utf-8")).hexdigest()
    except (TypeError, OSError):
        return ""


def hash_evaluator(experiment_runner_cls, score_pack_fn) -> str:
    """Hash the experiment runner class and score_pack function."""
    parts = [
        hash_callable_source(experiment_runner_cls),
        hash_callable_source(score_pack_fn),
    ]
    combined = "".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def hash_metrics_module(metrics_module) -> str:
    """Hash key scoring functions from metrics module."""
    key_functions = [
        "evaluate_session_restore",
        "recall_accuracy",
        "token_usage",
        "pack_sufficiency",
        "contamination_rate",
    ]
    parts = []
    for name in key_functions:
        fn = getattr(metrics_module, name, None)
        if fn:
            parts.append(hash_callable_source(fn))
    combined = "".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
