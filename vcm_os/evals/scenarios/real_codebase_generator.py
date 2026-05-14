"""Generate eval scenarios from real git repositories."""
import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from vcm_os.evals.scenarios.types import EvalScenario
from vcm_os.schemas import EventRecord, SourcePointer, SourceType


@dataclass
class GitCommit:
    hash: str
    subject: str
    body: str
    files: List[str]
    diff_stat: str


def get_git_commits(repo_path: str, max_commits: int = 50) -> List[GitCommit]:
    """Extract commits from a git repository."""
    repo = Path(repo_path)
    if not (repo / ".git").exists():
        return []

    # Get commit hashes
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--format=%H", f"-{max_commits}"],
        capture_output=True, text=True, check=True,
    )
    hashes = result.stdout.strip().split("\n")

    commits = []
    for h in hashes:
        if not h:
            continue
        # Subject
        subj = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%s", h],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        # Body
        body = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%b", h],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        # Files changed
        files_res = subprocess.run(
            ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", h],
            capture_output=True, text=True, check=True,
        )
        files = [f for f in files_res.stdout.strip().split("\n") if f]
        # Diff stat
        stat_res = subprocess.run(
            ["git", "-C", str(repo), "show", "--stat", "--oneline", h],
            capture_output=True, text=True, check=True,
        )
        diff_stat = stat_res.stdout.strip()

        commits.append(GitCommit(hash=h, subject=subj, body=body, files=files, diff_stat=diff_stat))

    return commits


def commits_to_scenario(
    repo_path: str,
    commits: List[GitCommit],
    project_name: str,
    query: Optional[str] = None,
) -> EvalScenario:
    """Convert a sequence of commits into an EvalScenario."""
    repo = Path(repo_path)
    project_id = f"real_{project_name}_{hashlib.md5(str(repo).encode()).hexdigest()[:8]}"
    session_id = f"sess_{project_name}_{commits[0].hash[:8]}"

    # Build events from commits
    from datetime import datetime, timezone, timedelta
    base_time = datetime.now(timezone.utc) - timedelta(hours=len(commits))
    events = []
    for i, c in enumerate(commits):
        ts = base_time + timedelta(minutes=i)
        # User message: commit subject as intent/goal
        events.append(EventRecord(
            event_id=f"evt_{c.hash[:8]}_msg",
            project_id=project_id,
            timestamp=ts,
            event_type="user_message",
            raw_text=c.subject,
            source_type=SourceType.USER_MESSAGE,
        ))
        # Code change: files and diff stat
        if c.files:
            events.append(EventRecord(
                event_id=f"evt_{c.hash[:8]}_diff",
                project_id=project_id,
                timestamp=ts + timedelta(seconds=30),
                event_type="code_change",
                raw_text=f"Changed files: {', '.join(c.files[:5])}\n{c.diff_stat[:500]}",
                source_type=SourceType.CODE_DIFF,
            ))

    # Derive expected goals from commit subjects
    expected_goals = [c.subject for c in commits[:3]]
    # Derive expected decisions from commit bodies (lines starting with "Decision:" or containing "use ")
    expected_decisions = []
    for c in commits:
        for line in c.body.split("\n"):
            line = line.strip()
            if line.lower().startswith("decision:") or line.lower().startswith("use "):
                expected_decisions.append(line)
    expected_decisions = expected_decisions[:3] or ["Implement feature"]

    # Derive critical gold from file names
    critical_gold = set()
    for c in commits:
        for f in c.files:
            parts = f.split("/")
            critical_gold.update(parts)
    critical_gold = {w for w in critical_gold if len(w) > 3 and w not in ("src", "test", "tests", "lib", "docs")}
    critical_gold = set(list(critical_gold)[:10])

    # Auto-generate query if not provided
    if query is None:
        # Use most frequent words from subjects
        words = {}
        for c in commits:
            for w in c.subject.lower().split():
                if len(w) > 3:
                    words[w] = words.get(w, 0) + 1
        top_words = sorted(words.items(), key=lambda x: -x[1])[:3]
        query = " ".join(w for w, _ in top_words) or "recent changes"

    return EvalScenario(
        name=f"real_{project_name}_{commits[0].hash[:8]}",
        project_id=project_id,
        events=events,
        expected_goals=expected_goals,
        expected_decisions=expected_decisions,
        expected_errors=[],
        expected_answer_keywords=list(critical_gold)[:5],
        critical_gold=list(critical_gold),
        protected_terms=[],
        test_query=query,
    )


def generate_real_codebase_scenarios(repos: List[str], commits_per_scenario: int = 5) -> List[EvalScenario]:
    """Generate scenarios from multiple real repos."""
    scenarios = []
    for repo_path in repos:
        repo = Path(repo_path)
        if not repo.exists():
            continue
        commits = get_git_commits(repo_path, max_commits=50)
        if len(commits) < commits_per_scenario:
            continue

        # Create multiple scenarios per repo by sliding window
        project_name = repo.name.replace(".", "_").replace("-", "_")
        step = max(1, commits_per_scenario // 2)
        for i in range(0, len(commits) - commits_per_scenario + 1, step):
            chunk = commits[i:i + commits_per_scenario]
            sc = commits_to_scenario(repo_path, chunk, project_name)
            scenarios.append(sc)

    return scenarios
