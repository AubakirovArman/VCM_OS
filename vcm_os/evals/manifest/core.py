"""Canonical evaluation manifest dataclass and serialization."""
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class EvalManifest:
    """Immutable attestation of an evaluation run."""

    manifest_version: str = "v0.7_eval_manifest_001"
    system_version: str = "v0.5-gold"
    eval_phase: str = "v0.6-generalization"
    report_version: str = ""
    git_commit: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Code hashes
    runner_hash: str = ""
    evaluator_hash: str = ""
    pack_builder_hash: str = ""
    retrieval_config_hash: str = ""
    metrics_hash: str = ""

    # Infrastructure
    embedding_model: str = "BGE-small-en-v1.5"
    llm: str = "Gemma 4 31B via vLLM"
    random_seed: str = ""
    tokenizer_version: str = ""

    # Scenario sets with per-scenario hashes
    scenario_sets: Dict[str, Dict] = field(default_factory=dict)

    # Audit flags
    audit: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def compute_fingerprint(self) -> str:
        """Deterministic SHA-256 of the manifest (excluding itself)."""
        payload = self.to_json()
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "EvalManifest":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
