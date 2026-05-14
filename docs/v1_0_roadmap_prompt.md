# VCM-OS v1.0 Roadmap & Research Prompt

> **Project:** VCM-OS (Virtual Context Memory Operating System)  
> **Current Version:** v0.9.2 (baseline comparison + semantic matching complete)  
> **Date:** 2026-05-10  
> **Purpose:** Research prompt for continuing VCM-OS development toward v1.0

---

## 1. Executive Summary

VCM-OS — это слой виртуализации контекста над LLM-агентом (Gemma 4 31B). Цель: заменить подход "всё прошлое в prompt" на подход "агент запрашивает у memory layer минимальный достаточный набор проверяемых воспоминаний для текущей задачи".

Текущий статус: **v0.9.2 complete**. Получены честные baseline-сравнения (VCM vs RawVerbatim vs StrongRAG vs Full Context). VCM побеждает RawVerbatim на 25/29 tuning-сценариях, но проигрывает по token efficiency. Holdout показывает verbatim ceiling ~0.72.

Нужно перейти к **v1.0: real-codebase integration + token optimization + learned router**.

---

## 2. What Has Already Been Built (v0.1 → v0.9.2)

### v0.1 Core ✅
- Event-sourced typed memory (decision/error/intent/requirement/task/code_change/uncertainty/goal)
- SQLite store + session checkpoint/restore
- Decision ledger + Error ledger
- Dense (BGE-small-en-v1.5) + sparse (BM25) retrieval
- Context pack builder with token budget
- FastAPI server (port 8123)

### v0.2 Advanced Retrieval ✅
- RRF fusion reranker
- LLM query rewriter
- Graph expansion (multi-hop)
- Reflection engine (evidence-gated)
- Typed decay engine (half-life per memory type)
- Stale checker + superseded filter
- Pack sufficiency checker
- Adaptive compression

### v0.3 Codebase & Verifier ✅
- AST-based Python code indexer
- Symbol graph (call graph, dependencies)
- Consistency verifier (contradiction, contamination, citation)
- Summary generator

### v0.5-v0.6 Eval System ✅
- 23+ synthetic scenarios (multi-session, stale facts, cross-project, false memory)
- Baselines: Summary, RAG, Full Context
- Experiments: T10, H03, S05, F03, I01
- Automated report generation

### v0.7 Audit System ✅
- Canonical eval manifest (frozen holdout)
- MUTATION_LOG.json (audit trail)
- 15 component metrics
- Project State Object (PSO)
- VCM trace per run
- quality_v0_7 composite scoring

### v0.8 Exact Symbol Vault ✅
- SymbolVaultEntry schema (env_var, api_endpoint, cve, package_version, config_key, ci_job, function_name)
- SQLite store + retriever + pack slot
- Holdout restore: 0.733 → 1.000 (with fallback)
- Tokens: 132 → 82.3

### v0.9 Baselines ✅
- RawVerbatim baseline (raw events, no LLM extraction, dense+sparse+keyword+temporal+exact-symbol)
- StrongRAG baseline (RAG + BM25 + rerank + stale filter + exact-symbol boost)
- Full Context baseline (all memories)

### v0.9.1 Semantic Matching ✅
- BGE-embedding semantic goal/decision matcher (cosine similarity)
- Goal extraction from events
- Per-query audit JSONL

### v0.9.2 Threshold Ablation + Tuning Eval ✅
- Semantic thresholds tested: 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
- **Recommended threshold: 0.75**
- Tuning eval: 29 scenarios, VCM wins RawVerbatim 25/29

---

## 3. What Has Been Proven

### Holdout Results (20 frozen scenarios)

| Metric | VCM | RawVerbatim | StrongRAG | Full |
|--------|-----|-------------|-----------|------|
| restore (exact-symbol) | 1.000 | 1.000 | 1.000 | 1.000 |
| verbatim | 0.717 | 0.717 | 0.717 | 0.717 |
| semantic (0.75) | 0.900 | — | — | — |
| tokens | 83.5 | **53.0** | 137.2 | 224.4 |
| stale | **0.000** | 0.300 | 0.000 | 0.300 |
| quality | **0.688** | 0.567 | 0.643 | 0.605 |

### Tuning Results (29 scenarios)

| Metric | VCM | RawVerbatim | StrongRAG |
|--------|-----|-------------|-----------|
| restore | **0.816** | 0.747 | 0.747 |
| verbatim | **0.782** | 0.724 | 0.724 |
| tokens | 90.7 | **54.9** | 133.2 |
| stale | 0.000 | 0.000 | 0.000 |
| quality | **0.694** | 0.631 | 0.608 |
| win count | **25/29** | 4/29 | 0/29 |

### Key Insights
1. **Verbatim ceiling is ~0.72** on holdout — goals are semantic paraphrases, not verbatim in events
2. **VCM's real wins:** stale suppression (0.000), project state (0.292), multi-fact scenarios
3. **RawVerbatim's win:** token efficiency (53 vs 84), exact-symbol preservation
4. **StrongRAG is not competitive** — too many tokens for same verbatim result
5. **Semantic matching at 0.75** gives honest 0.90 overall — use this for publication

---

## 4. What Does NOT Work / Active Blockers

### Blocker 1: Token Inflation (HIGH PRIORITY)
- VCM uses 83.5 tokens (holdout) / 90.7 (tuning) vs RawVerbatim 53-55
- Target: ≤60 tokens to beat RawVerbatim on efficiency
- Root cause: structured sections add overhead; per-item caps don't compress enough

### Blocker 2: Verbatim Ceiling (MEDIUM)
- 0.717 ceiling on holdout because expected_goals don't appear verbatim in events
- No amount of retrieval improvement can fix this without goal extraction
- Semantic matching (0.75) gives 0.90 but is not "real" verbatim

### Blocker 3: Exact-Symbol Fallback Inflates Scores (MEDIUM)
- All methods get 1.000 with exact-symbol fallback
- This hides real differences between methods
- Need per-scenario analysis without fallback

### Blocker 4: Rationale Recall is Stub (0.200) (MEDIUM)
- Not a real metric yet
- Need to extract rationale from events and check if present in pack

### Blocker 5: Real Codebase Gap (HIGH PRIORITY)
- All evals on synthetic scenarios
- Real codebase restore historically 0.17-0.33
- Need real-project dogfooding

### Blocker 6: Symbol Vault Auto-Extraction (LOW)
- Currently populated from eval scenario terms
- No automatic extraction from real events
- Need pattern-based extractor for config keys, API endpoints, env vars

### Blocker 7: VCM Not Integrated Into Live Workflow (HIGH PRIORITY)
- Kimi Code CLI talks directly to Gemma 4 (:8000)
- VCM-OS server (:8123) runs separately but is not called by client
- Needs adapter: FastAPI proxy, MCP server, or CLI wrapper

### Blocker 8: Tuning Tokens Above Target (MEDIUM)
- Tuning avg 90.7 tokens vs holdout 83.5
- Target was ≤84 tokens
- Need further compression for tuning scenarios

---

## 5. v1.0 Roadmap

### Phase A: Token Optimization (v0.10)
**Goal:** Match RawVerbatim token efficiency (≤60 tokens) without losing restore

**Tasks:**
1. Aggressive per-section compression (merge similar memories)
2. Dynamic section budgets based on query type
3. Remove redundant section headers ("Decisions:", "Errors:")
4. Inline format: `dec: use Redis | err: auth loop | goal: idempotent payments`
5. Test on holdout: target 60 tokens, restore ≥0.70

### Phase B: Real Codebase Integration (v0.11)
**Goal:** Prove VCM works on actual coding projects

**Tasks:**
1. Create adapter layer for Kimi Code CLI → VCM-OS server
2. Index real project (this repo: `/mnt/hf_model_weights/arman/3bit/VCM_OS`)
3. Run real coding session with VCM memory layer
4. Measure: can VCM restore project state after 24h break?
5. Compare: VCM pack vs raw chat history for same task

### Phase C: Learned Memory Router (v0.12)
**Goal:** Replace heuristic router with learned policy

**Tasks:**
1. Collect training data from eval runs (query → optimal retrieval plan)
2. Train small classifier (BGE-small or smaller) for task-type routing
3. Compare: learned router vs heuristic router on holdout
4. Metric: context_usefulness score improvement

### Phase D: Multi-Agent Memory Manager (v0.13)
**Goal:** Split memory operations into specialized agents

**Tasks:**
1. Memory Writer agent (small model, fast)
2. Memory Retriever agent (router + retrieval)
3. Contradiction Detector agent
4. Project Librarian agent (PSO maintainer)
5. Compare latency/quality vs monolithic VCM

### Phase E: GraphRAG Integration (v0.14)
**Goal:** Add knowledge graph for multi-hop reasoning

**Tasks:**
1. Extract entities/relations from memories
2. Build graph (files, functions, decisions, errors)
3. Graph expansion at retrieval time
4. Test on multi-hop scenarios (e.g., "What depends on auth middleware?")

### Phase F: Publication Prep (v1.0)
**Goal:** Package for academic/industry publication

**Tasks:**
1. Final holdout run (frozen scenarios, no tuning)
2. Human evaluation of semantic matches
3. Ablations: remove each component, measure drop
4. Comparison with MemGPT, GraphRAG, LongMem baselines
5. Write paper / technical report

---

## 6. Research Prompt for ChatGPT Pro

Use this prompt to continue VCM-OS development:

```text
Ты работаешь как lead researcher и principal engineer проекта VCM-OS — Virtual Context Memory Operating System для LLM-агентов.

Контекст проекта:
- VCM-OS — это слой виртуализации контекста над LLM (Gemma 4 31B через vLLM)
- Сейчас версия v0.9.2, реализовано: event-sourced typed memory, hybrid retrieval (dense+sparse+BM25), RRF reranker, session store, decision/error ledgers, AST codebase index, consistency verifier, eval harness (23+ synthetic scenarios), exact-symbol vault, semantic matching
- Текущие результаты: VCM побеждает RawVerbatim baseline на 25/29 tuning-сценариях, но проигрывает по token efficiency (83.5 vs 53.0 tokens)
- Verbatim ceiling на holdout: 0.717 (semantic paraphrase problem)
- All tests pass (29/29)

Главная цель: перейти к v1.0 через 6 фаз:
A. Token optimization (target ≤60 tokens)
B. Real codebase integration (adapter for Kimi Code CLI)
C. Learned memory router (replace heuristic routing)
D. Multi-agent memory manager (specialized agents)
E. GraphRAG integration (multi-hop reasoning)
F. Publication prep (human eval, ablations, paper)

Твоя задача:
1. Выбери ОДНУ фазу для работы (начни с A или B)
2. Сформулируй гипотезы о том, что даст наибольший прирост
3. Предложи конкретные изменения кода (файлы, функции, алгоритмы)
4. Определи метрики успеха
5. Найди риски и trade-offs
6. Создай пошаговый план реализации

Ограничения:
- Не переписывай всё с нуля. Делай минимальные изменения.
- Сохраняй backward compatibility (все 29 тестов должны проходить)
- Не используй внешние API — всё локально (SQLite, BGE-small, Gemma 4 31B)
- Python 3.13, torch 2.8, FastAPI

Формат ответа:
1. Выбранная фаза и обоснование
2. Гипотезы (3-5)
3. Конкретные изменения (файлы + псевдокод)
4. Метрики успеха
5. Риски и mitigation
6. Пошаговый план (шаги 1-N)
7. Self-review: 5 слабых мест плана

Не оптимизируй ответ под убедительность. Оптимизируй под проверяемое качество результата.
```

---

## 7. Files Reference

### Core Implementation
| File | Purpose |
|------|---------|
| `vcm_os/schemas/` | Pydantic models for all objects |
| `vcm_os/memory/store.py` | SQLite metadata store |
| `vcm_os/memory/writer/` | Rule-based + LLM memory extraction |
| `vcm_os/memory/reader.py` | Hybrid retrieval (dense+sparse+keyword) |
| `vcm_os/memory/router.py` | Task-aware memory routing |
| `vcm_os/memory/decay.py` | Typed half-life decay |
| `vcm_os/context/pack_builder/` | Context pack assembly |
| `vcm_os/context/reranker.py` | RRF fusion |
| `vcm_os/evals/` | Eval harness + baselines + metrics |
| `vcm_os/memory/symbol_vault/` | Exact symbol storage |
| `main.py` | FastAPI server |

### Eval & Results
| File | Purpose |
|------|---------|
| `docs/v0_9_complete_results.md` | Full v0.9 analysis |
| `docs/holdout_v0_9_comparison.json` | Holdout per-scenario results |
| `docs/tuning_v0_9_results.json` | Tuning per-scenario results |
| `docs/threshold_ablation.json` | Semantic threshold sweep |
| `MUTATION_LOG.json` | Audit trail for holdout |

### Scripts
| File | Purpose |
|------|---------|
| `run_v0_9_comparison.py` | Run 4-method comparison |
| `run_tuning_v0_9.py` | Run tuning eval |
| `run_threshold_ablation.py` | Run threshold sweep |
| `verify_system.py` | Full system check |

---

## 8. Quick Commands

```bash
# Tests
pytest tests/ -v

# Server
python main.py

# Evals
python run_v0_9_comparison.py
python run_tuning_v0_9.py
python run_threshold_ablation.py

# Verification
python verify_system.py
```

---

## 9. Next Immediate Action

**Recommended:** Start Phase A (Token Optimization) because:
1. Lowest risk — changes only to pack builder formatting
2. Highest impact — closes gap with RawVerbatim on efficiency
3. Enables real integration (user won't accept 2x token overhead)
4. Does not require new dependencies

**Alternative:** Start Phase B (Real Integration) if you want immediate practical value.

---

*Document generated: 2026-05-10*  
*VCM-OS v0.9.2 → v1.0 Roadmap*
