"""Scenario mutation log: tracks freeze dates, commits, and changes."""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

MUTATION_LOG_PATH = Path("MUTATION_LOG.json")


@dataclass
class ScenarioMutationEntry:
    scenario_name: str
    first_seen_commit: str = ""
    freeze_date: str = ""
    frozen: bool = False
    mutation_count: int = 0
    mutations: List[Dict] = field(default_factory=list)


@dataclass
class MutationLog:
    log_version: str = "v0.7_mutation_log_001"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    entries: Dict[str, ScenarioMutationEntry] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "log_version": self.log_version,
            "created_at": self.created_at,
            "entries": {k: asdict(v) for k, v in self.entries.items()},
        }

    def save(self, path: str = None) -> None:
        path = path or str(MUTATION_LOG_PATH)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

    @classmethod
    def load(cls, path: str = None) -> "MutationLog":
        path = path or str(MUTATION_LOG_PATH)
        if not Path(path).exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log = cls(log_version=data.get("log_version", "v0.7_mutation_log_001"))
        log.created_at = data.get("created_at", log.created_at)
        for name, entry in data.get("entries", {}).items():
            log.entries[name] = ScenarioMutationEntry(**entry)
        return log

    def get_frozen_ids(self) -> List[str]:
        return sorted([name for name, e in self.entries.items() if e.frozen])

    def validate_against_run(self, run_scenario_names: List[str]) -> Dict:
        frozen = set(self.get_frozen_ids())
        ran = set(run_scenario_names)
        missing = sorted(frozen - ran)
        extra = sorted(ran - frozen)
        return {
            "frozen_ids": sorted(frozen),
            "ran_ids": sorted(ran),
            "missing_from_run": missing,
            "extra_not_frozen": extra,
            "all_frozen_present": len(missing) == 0,
        }
