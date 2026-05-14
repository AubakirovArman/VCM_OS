# Component Ablation Study (v0.10)

**Date:** 2026-05-10  
**Dataset:** 20 frozen holdout scenarios  
**Metric:** `restore` (overall recall), `quality` (composite score)

---

## Results

| Component Removed | Δ restore | Δ quality | Δ tokens | Notes |
|-------------------|-----------|-----------|----------|-------|
| **Baseline** | 0.942 | 1.900 | 67.2 | — |
| No stale filter | 0.000 | **−0.300** | +1.3 | Stale suppression critical for quality |
| No adaptive cap | **−0.017** | −0.067 | 0.0 | Protects exact symbols from truncation |
| No symbol vault | 0.000 | −0.025 | −1.5 | Minor on holdout; critical for real symbols |
| No PSO | 0.000 | 0.000 | **−15.6** | PSO adds tokens; holdout has few PSO-relevant scenarios |
| No reranker | 0.000 | 0.000 | 0.0 | Reranker does not affect top-50 on holdout |
| No compact assembly | 0.000 | 0.000 | 0.0 | Format change; token count same |

---

## Key Findings

### 1. Stale Suppression is Critical
Removing stale filter drops quality by **0.300** (15.8% relative). This confirms v0.7 stale suppression is the single most impactful component for quality.

### 2. Adaptive Cap Protects Exact Symbols
Removing adaptive cap (100 chars for protected terms) drops restore by **0.017** and quality by **0.067**. On holdout, this affects exact-symbol scenarios (`exact_config_key`, `exact_api_endpoint`).

### 3. Symbol Vault Minor on Holdout
Removing SV drops quality by only **0.025** because holdout scenarios have short symbols that survive truncation without SV. Real-world scenarios with long symbols (e.g., `transformers.models.llama.modeling_llama.LlamaModel`) benefit significantly.

### 4. PSO Adds Tokens Without Restore Benefit on Holdout
PSO adds ~15.6 tokens but does not improve restore on holdout. This is expected: holdout scenarios query specific events, not project state. PSO is designed for project-switching and state-recovery tasks (H03, I01).

### 5. Reranker Redundant on Holdout
Reranker does not change results because holdout scenarios have few distractors. Reranker matters for adversarial_hard (20+ distractors).

---

## Publication Summary

```
Component impact (sorted by |Δquality|):
  1. Stale filter      : |Δquality| = 0.300  → CRITICAL
  2. Adaptive cap      : |Δquality| = 0.067  → IMPORTANT
  3. Symbol vault      : |Δquality| = 0.025  → MINOR (holdout)
  4. PSO               : |Δquality| = 0.000  → TASK-SPECIFIC
  5. Reranker          : |Δquality| = 0.000  → ADVERSARIAL-SPECIFIC
```
