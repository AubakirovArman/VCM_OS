"""Hash runtime configuration for evaluation reproducibility."""
import hashlib
import json
from typing import Dict


def hash_retrieval_config(
    top_k: int = 50,
    token_budget: int = 32768,
    vector_weight: float = 0.7,
    sparse_weight: float = 0.3,
    rrf_k: int = 60,
    reranker_top_n: int = 20,
    decay_half_life_days: float = 30.0,
    stale_check_enabled: bool = True,
    graph_expansion_hops: int = 2,
) -> str:
    """Hash retrieval and pack-building hyperparameters."""
    cfg = {
        "top_k": top_k,
        "token_budget": token_budget,
        "vector_weight": vector_weight,
        "sparse_weight": sparse_weight,
        "rrf_k": rrf_k,
        "reranker_top_n": reranker_top_n,
        "decay_half_life_days": decay_half_life_days,
        "stale_check_enabled": stale_check_enabled,
        "graph_expansion_hops": graph_expansion_hops,
    }
    text = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
