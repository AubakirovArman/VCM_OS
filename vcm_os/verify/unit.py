"""Unit test verification runner."""
import subprocess
import sys


def run_unit_tests() -> bool:
    print("\n=== Running Unit Tests ===")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode == 0
