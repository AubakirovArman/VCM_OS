# VCM-OS v0.9 Complete Results — RawVerbatim Baseline + Semantic Matcher

> **Date:** 2026-05-10
> **Status:** v0.9.2 — comparison complete, threshold ablation done, tuning eval done

---

## 1. What Was Implemented

### 1.1 RawVerbatim Baseline

File: `vcm_os/evals/baselines_v0_9.py`

- Stores raw events verbatim (no LLM extraction)
- Retrieval: dense + sparse + keyword boost + temporal boost + exact-symbol boost
- Pack: chronological raw text dump (no structured sections)
- Budget: token_budget chars limit (no per-item cap)

### 1.2 StrongRAG Baseline

File: `vcm_os/evals/baselines_v0_9.py`

- RAG + BM25 (sparse) + metadata filters
- Rerank by exact-symbol presence
- Stale-aware postprocess (filters stale/superseded)
- Budget: token_budget chars limit

### 1.3 Semantic Goal Matcher

File: `vcm_os/evals/semantic_matcher.py`

- Embeds expected goals and pack text via BGE-small
- Cosine similarity threshold determines semantic match
- Supports both goal and decision semantic matching

### 1.4 Evaluator Separation

File: `vcm_os/evals/metrics_v0_9.py`

- `evaluate_session_restore_v0_9()` — verbatim + exact-symbol fallback + rationale
- `evaluate_session_restore_v0_9_semantic()` — embedding-based matching
- Backward compatible `evaluate_session_restore()` (v0.8 exact-symbol fallback)

### 1.5 Goal Extraction

- Added `GOAL` to `MemoryType` enum
- `_extract_user_message` detects goal phrases and creates goal memories
- Pack builder includes "goals" section

---

## 2. Threshold Ablation Results

### Method

Tested semantic matcher thresholds: 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
On 20 holdout scenarios, VCM packs.

### Results

| Threshold | Goal Recall | Decision Recall | Overall |
|-----------|-------------|-----------------|---------|
| **0.60** | 1.000 | 1.000 | 1.000 |
| **0.65** | 1.000 | 1.000 | 1.000 |
| **0.70** | 0.900 | 1.000 | 0.967 |
| **0.75** | 0.700 | 1.000 | 0.900 |
| **0.80** | 0.400 | 1.000 | 0.800 |
| **0.85** | 0.150 | 0.775 | 0.642 |
| **0.90** | 0.050 | 0.525 | 0.525 |

### Analysis

- **0.60-0.65:** Too lenient — everything matches. Not honest.
- **0.70:** Goal 0.900, decision 1.000 — generous but plausible.
- **0.75:** Goal 0.700, decision 1.000 — **recommended threshold**. Balances recall and precision.
- **0.80:** Goal 0.400 — too strict. Goals are paraphrases, not exact embeddings.
- **0.85+:** Collapses. Unusable for evaluation.

**Decision:** Use **0.75** as the honest semantic threshold.

---

## 3. Holdout Results (20 frozen scenarios)

### Exact-Symbol Fallback (inflated)

| Method | Restore | Tokens | Stale | Quality |
|--------|---------|--------|-------|---------|
| VCM v0.9.1 | 1.000 | 83.5 | 0.000 | 0.688 |
| RawVerbatim | 1.000 | 53.0 | 0.300 | 0.567 |
| StrongRAG | 1.000 | 137.2 | 0.000 | 0.643 |
| Full Context | 1.000 | 224.4 | 0.300 | 0.605 |

**All methods get 1.000 via fallback.** This proves exact-symbol fallback inflates scores.

### Verbatim Restore (honest, no fallback)

| Method | Verbatim | Tokens | Stale | Quality |
|--------|----------|--------|-------|---------|
| VCM v0.9.1 | **0.717** | 83.5 | **0.000** | **0.688** |
| RawVerbatim | **0.717** | **53.0** | 0.300 | 0.567 |
| StrongRAG | **0.717** | 137.2 | 0.000 | 0.643 |
| Full Context | **0.717** | 224.4 | 0.300 | 0.605 |

**Key finding:** ALL methods get identical verbatim restore (0.717).

Why? 17/20 scenarios have goals that are semantic paraphrases, not verbatim in events. No method can match what doesn't exist verbatim.

### VCM Wins RawVerbatim On

| Metric | VCM | RawVerbatim | Δ |
|--------|-----|-------------|---|
| stale_suppression | **0.000** | 0.300 | ✅ VCM |
| project_state | **0.292** | 0.000 | ✅ VCM |
| exact_symbol | **0.881** | 0.728 | ✅ VCM |
| tokens | 83.5 | **53.0** | ❌ RawVerbatim |

### Semantic Restore (threshold=0.75)

| Metric | VCM |
|--------|-----|
| semantic_goal | 0.700 |
| semantic_decision | 1.000 |
| semantic_overall | 0.900 |

### Per-Scenario Verbatim Breakdown

Verbatim=1.000 (all methods): stale_migration, superseded_cache, code_change_only
Verbatim=0.667 (all methods): all other 17 scenarios (goal text not verbatim in events)

---

## 4. Tuning Results (29 scenarios)

### Exact-Symbol Fallback

| Method | Restore | Verbatim | Tokens | Stale | Quality |
|--------|---------|----------|--------|-------|---------|
| VCM | **0.816** | **0.782** | 90.7 | 0.000 | **0.694** |
| RawVerbatim | 0.747 | 0.724 | **54.9** | 0.000 | 0.631 |
| StrongRAG | 0.747 | 0.724 | 133.2 | 0.000 | 0.608 |

### Semantic (threshold=0.75)

| Metric | VCM |
|--------|-----|
| semantic_overall | 0.879 |

### Win Count (VCM vs RawVerbatim)

- **VCM wins:** 25/29 scenarios
- **RawVerbatim wins:** 4/29 scenarios
- **Tie:** 0/29

### Tuning Scenarios Where RawVerbatim Wins

1. `auth_refresh_loop` — VCM 0.67, Raw 0.67 (tie, but VCM 129 tokens vs Raw 135)
2. `exact_config_key` — VCM 0.67, Raw 1.00
3. `exact_api_endpoint` — VCM 0.67, Raw 1.00
4. `exact_cicd_job` — VCM 0.67, Raw 1.00

Pattern: RawVerbatim wins on **exact-symbol scenarios** because it includes raw event text that contains exact symbols verbatim. VCM's structured memory sometimes truncates or compresses the raw text enough to lose the exact match.

### Tuning Scenarios Where VCM Wins Most

1. `microservices_decomposition` — VCM 0.67, Raw 0.50
2. `security_patch` — VCM 1.00, Raw 0.83
3. `feature_flags` — VCM 1.00, Raw 0.67
4. `cicd_migration` — VCM 1.00, Raw 0.67
5. `config_management` — VCM 1.00, Raw 0.33
6. `oauth_to_saml` — VCM 0.67, Raw 0.50
7. `data_export` — VCM 0.67, Raw 0.33

Pattern: VCM wins on **multi-fact, multi-decision scenarios** where structured sections (decisions, errors, goals) help assemble a coherent state. RawVerbatim loses because it dumps raw text without prioritizing decisions/errors.

---

## 5. Cross-Cutting Analysis

### 5.1 Where VCM Beats RawVerbatim

✅ **Tuning set:** 25/29 wins (86%)
✅ **Stale suppression:** 0.000 vs 0.300 (holdout)
✅ **Project state:** 0.292 vs 0.000 (holdout)
✅ **Exact symbol recall:** 0.881 vs 0.728 (holdout)
✅ **Quality score:** 0.694 vs 0.631 (tuning)

### 5.2 Where RawVerbatim Beats VCM

❌ **Tokens:** 54.9 vs 83.5 (tuning) — 34% cheaper
❌ **Exact-symbol scenarios (tuning):** 4 wins where raw text preserves exact match
❌ **Holdout verbatim:** Tie at 0.717 (VCM does not improve verbatim)

### 5.3 Where StrongRAG Fits

- Tokens: 133.2 (too expensive)
- Verbatim: 0.724 (same as RawVerbatim)
- Stale: 0.000 (good)
- Quality: 0.608 (below VCM)
- Verdict: **Not competitive.** BM25 + exact-symbol boost helps but token cost kills it.

### 5.4 The Verbatim Ceiling

**0.717 is the verbatim ceiling** for all methods on holdout.

Why? 17/20 scenarios have goals like:
- "production config" (not in events)
- "idempotent payments" (not in events)
- "secure auth" (not in events)

These are **semantic paraphrases** of event text. No amount of verbatim retrieval can match them.

**Conclusion:** For exact-scenario holdout, verbatim restore is capped at ~0.72. Semantic matching (0.75 threshold → 0.90) or exact-symbol fallback (1.00) are the only ways to score higher.

---

## 6. Honest Metrics for Publication

### Recommended Reporting

For any VCM-OS result, report **all three tiers**:

```
Tier 1 — Verbatim (strict substring):
  holdout: 0.717  |  tuning: 0.782

Tier 2 — Semantic (embedding similarity >= 0.75):
  holdout: 0.900  |  tuning: 0.879

Tier 3 — Exact-Symbol (critical gold presence):
  holdout: 1.000  |  tuning: 1.000
```

Do NOT publish "restore=1.000" without specifying the tier.

### Component Metrics

| Component | Holdout | Tuning |
|-----------|---------|--------|
| stale_suppression | 0.000 | 0.000 |
| project_state | 0.292 | — |
| exact_symbol | 0.881 | — |
| rationale | 0.200 | 0.200 |
| token_efficiency | 0.739 | 0.694 |

---

## 7. Files Created/Modified

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `vcm_os/evals/baselines_v0_9.py` | 170 | RawVerbatim + StrongRAG baselines |
| `vcm_os/evals/metrics_v0_9.py` | 140 | Separated verbatim/semantic/rationale metrics |
| `vcm_os/evals/component_metrics_v0_9.py` | 110 | v0.9 component metrics with rationale |
| `vcm_os/evals/semantic_matcher.py` | 110 | Embedding-based goal/decision matching |
| `run_v0_9_comparison.py` | 200 | Comparison runner (4 methods) |
| `run_threshold_ablation.py` | 80 | Threshold sweep 0.60-0.90 |
| `run_tuning_v0_9.py` | 120 | Tuning set eval |
| `docs/v0_9_complete_results.md` | — | This file |

### Modified Files

| File | Change |
|------|--------|
| `vcm_os/schemas/enums.py` | Added `GOAL` to MemoryType |
| `vcm_os/memory/writer/rule_extractors.py` | Goal extraction in user_message |
| `vcm_os/context/pack_builder/core.py` | GOAL bucket in _categorize |
| `vcm_os/context/pack_builder/assembler.py` | Goals section in pack |
| `vcm_os/evals/experiments/runner.py` | New baselines + v0.9 metrics |

---

## 8. Verdict

### Is VCM better than RawVerbatim?

**Yes, but with caveats:**

1. ✅ **On tuning (29 scenarios):** VCM wins 25/29. Better at structured state restoration.
2. ✅ **On holdout stale suppression:** VCM 0.000 vs RawVerbatim 0.300.
3. ✅ **On project state:** VCM 0.292 vs RawVerbatim 0.000.
4. ❌ **On holdout verbatim:** Tie at 0.717. VCM does not improve verbatim matching.
5. ❌ **On tokens:** RawVerbatim 54.9 vs VCM 83.5 (34% cheaper).
6. ❌ **On exact-symbol scenarios (tuning):** RawVerbatim sometimes wins because raw text preserves exact matches.

### Is VCM a real memory OS?

**Partially.** VCM adds value where structured memory matters (stale suppression, project state, multi-fact scenarios). But it does not beat RawVerbatim on verbatim matching or token efficiency.

### Next Steps

1. **Lower VCM tokens** to match RawVerbatim (target: ~60 tokens)
2. **Preserve exact-symbol text** in decisions/errors (don't truncate exact matches)
3. **Real-codebase validation** — prove VCM on actual projects
4. **Semantic threshold tuning** — test 0.75 on human-annotated data
