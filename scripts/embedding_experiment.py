#!/usr/bin/env python3
"""Embedding model upgrade experiment — benchmark retrieval quality vs latency."""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import MemoryRequest
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


MODELS = {
    "bge-small": "BAAI/bge-small-en-v1.5",  # 384d, current
    "bge-base": "BAAI/bge-base-en-v1.5",    # 768d
}


def benchmark_model(model_name: str, model_path: str, scenarios, max_scenarios: int = 5):
    print(f"\n=== Benchmarking {model_name} ({model_path}) ===")

    # Load embedding model
    t0 = time.perf_counter()
    embedder = SentenceTransformer(model_path, device="cuda" if __import__("torch").cuda.is_available() else "cpu")
    load_time = time.perf_counter() - t0
    print(f"Model load: {load_time:.1f}s")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    # Use fresh index per model to avoid dimension mismatch
    import shutil
    from vcm_os.config import DATA_DIR
    index_path = Path(DATA_DIR) / "vector_index.pkl"
    if index_path.exists():
        index_path.unlink()
    vec = VectorIndex(model_name=model_path)
    vec._model = embedder
    sparse = SparseIndex()
    writer = MemoryWriter(store, vec, sparse)
    runner = ExperimentRunner(store, vec, sparse, writer)

    recalls = []
    latencies = []
    tokens = []

    for s in scenarios[:max_scenarios]:
        runner.ingest_scenario(s)

        # Measure retrieval latency
        req = MemoryRequest(
            project_id=s.project_id,
            query=s.test_query,
            task_type="general",
        )
        t0 = time.perf_counter()
        pack = runner.run_vcm(s)
        lat = time.perf_counter() - t0
        latencies.append(lat)

        score = runner.score_pack(pack, s)
        recalls.append(score.get("overall_restore", 0))
        tokens.append(score.get("token_usage", 0))

    import os
    os.unlink(db_path)

    return {
        "model": model_name,
        "model_path": model_path,
        "dimensions": embedder.get_sentence_embedding_dimension(),
        "load_time_sec": round(load_time, 2),
        "avg_recall": round(sum(recalls) / len(recalls), 3) if recalls else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000, 1) if latencies else 0,
        "avg_tokens": round(sum(tokens) / len(tokens), 1) if tokens else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Embedding model benchmark")
    parser.add_argument("--models", nargs="+", default=["bge-small"], choices=list(MODELS.keys()))
    parser.add_argument("--max-scenarios", type=int, default=5)
    parser.add_argument("--output", type=str, default="embedding_experiment_results.json")
    args = parser.parse_args()

    scenarios = load_holdout_scenarios()
    print(f"Loaded {len(scenarios)} holdout scenarios")

    results = []
    for name in args.models:
        path = MODELS[name]
        try:
            result = benchmark_model(name, path, scenarios, args.max_scenarios)
            results.append(result)
            print(f"Results: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"FAILED to benchmark {name}: {e}")
            results.append({"model": name, "error": str(e)})

    with open(args.output, "w") as f:
        json.dump({"results": results}, f, indent=2)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
