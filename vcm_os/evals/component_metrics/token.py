"""Token efficiency metrics."""
from typing import Dict

from vcm_os.schemas import ContextPack


def token_efficiency(pack: ContextPack, quality_score: float, full_context_tokens: int = 306) -> Dict[str, float]:
    """Quality-per-token and dynamic reduction metrics."""
    tokens = pack.token_estimate
    reduction = 1.0 - (tokens / full_context_tokens)
    return {
        "tokens": tokens,
        "reduction_ratio": reduction,
        "quality_per_token": quality_score / max(tokens, 1),
        "efficiency_score": quality_score * reduction,
    }
