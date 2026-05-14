"""Hash EvalScenario objects for manifest attestation."""
import hashlib
import json
from typing import Dict, List

from vcm_os.evals.scenarios.types import EvalScenario


def _stable_dict(d: Dict) -> str:
    """Deterministic JSON serialization."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def hash_scenario(scenario: EvalScenario) -> str:
    """Return SHA-256 hash of scenario content."""
    payload = {
        "name": scenario.name,
        "project_id": scenario.project_id,
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "raw_text": e.raw_text,
                "payload": _stable_dict(e.payload) if e.payload else "",
            }
            for e in scenario.events
        ],
        "expected_goals": scenario.expected_goals,
        "expected_decisions": scenario.expected_decisions,
        "expected_errors": scenario.expected_errors,
        "stale_facts": scenario.stale_facts,
        "test_query": scenario.test_query,
        "expected_answer_keywords": scenario.expected_answer_keywords,
        "critical_gold": scenario.critical_gold,
        "protected_terms": scenario.protected_terms,
        "locked": scenario.locked,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_scenario_set(scenarios: List[EvalScenario], set_name: str) -> Dict:
    """Return manifest-ready dict for a scenario set."""
    entries = []
    for sc in scenarios:
        entries.append({
            "name": sc.name,
            "hash": hash_scenario(sc),
            "locked": sc.locked,
        })
    combined = "".join(e["hash"] for e in entries)
    set_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return {
        "name": set_name,
        "count": len(entries),
        "set_hash": set_hash,
        "entries": entries,
    }
