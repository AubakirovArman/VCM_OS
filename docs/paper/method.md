# Method

## 1. Architecture Overview

VCM-OS is a modular context management system with four layers:

```
┌─────────────────────────────────────────┐
│  Layer 4: Context Pack Assembly         │
│  - Pack builder with budget allocation  │
│  - Compact inline format                │
│  - Hard token cap (84 default)          │
├─────────────────────────────────────────┤
│  Layer 3: Retrieval & Ranking           │
│  - Router (task-aware plan)             │
│  - Reader (dense + sparse)              │
│  - Scorer (RRF reranker)                │
│  - Stale filter                         │
├─────────────────────────────────────────┤
│  Layer 2: Typed Memory Store            │
│  - SQLite store with schema migrations  │
│  - Vector index (BGE-small-en-v1.5)     │
│  - Sparse index (BM25)                  │
│  - Project State Object (PSO)           │
│  - Exact Symbol Vault                   │
├─────────────────────────────────────────┤
│  Layer 1: Event Ingestion               │
│  - MemoryWriter with rule extractors    │
│  - Goal/decision/error detection        │
│  - Rationale preservation               │
│  - Ledger (decision/error tracking)     │
└─────────────────────────────────────────┘
```

## 2. Memory Schema

Each memory object has:
- `memory_type`: INTENT, DECISION, GOAL, ERROR, BUG, FILE, PROCEDURE, CONSTRAINT
- `validity`: ACTIVE, STALE, SUPERSEDED, REJECTED
- `compressed_summary`: ≤80 chars (100 for protected terms)
- `raw_text`: Full original text
- `metadata`: Timestamps, session ID, project ID, tags

## 3. Retrieval Pipeline

```
Query → Router (plan) → Reader (vector + sparse) → Scorer (RRF) → Stale Filter → Pack Builder
```

**Router**: Selects retrieval strategy based on task type (debugging, planning, review).

**Reader**: Retrieves top-K candidates from vector and sparse indexes.

**Scorer**: Reranks via Reciprocal Rank Fusion:
```python
score = sum(1.0 / (k + rank_i) for rank_i in ranks)
```

**Stale Filter**: Removes memories containing stale facts unless explicitly marked.

## 4. Pack Assembly

Task-aware section selection with budget allocation:
- Debugging: errors (2), decisions (2), code context (1)
- Planning: goals (2), decisions (2), open questions (1)
- Review: decisions (2), reflections (1), facts (1)

Compact inline format:
```
g=fix auth refresh loop; t=add tests; d=httpOnly cookie; b=refreshSession fails
```

Hard cap: trims non-critical sections if over `min(token_budget, 84)`.

## 5. Exact Symbol Vault

SQLite table `symbol_vault` with columns:
- `project_id`, `symbol`, `symbol_type`, `created_at`

Retrieval: fuzzy match on query terms, returns highest-scoring symbol.

Protected terms (from `critical_gold` + `protected_terms` in scenarios) get adaptive cap of 100 chars.

## 6. Evaluation Harness

- **52 scenarios**: 29 tuning + 20 holdout + 3 adversarial
- **Metrics**: restore (goal/decision/error recall), verbatim, semantic, exact-symbol, tokens, quality
- **Baselines**: Full Context, RAG, Summary, Raw Verbatim, Strong RAG
- **Ablations**: 8 components tested on holdout
