# VCM-OS RC4 → RC5+ Roadmap

**Status:** Post-RC4 Operational Memory Runtime
**Tests:** 84/84 passing
**CI Gates:** 9/9 passing

---

## Executive Summary

RC4 closed infrastructure gaps (verifier, redaction, multi-lang index, tool ingestion, CI gates, latency/load benchmarks). The system is now an **early operational memory runtime**, not just an eval prototype.

The next frontier is **Real Session Intelligence**: extracting goals/errors from noisy real session logs, linking memories into a graph, and making the system self-correcting.

---

## What RC4 Proved

| Area | Status |
|------|--------|
| Infrastructure maturity | ✅ Strong |
| Stale-free memory | ✅ Strong |
| Exact symbol + tool ingestion | ✅ Medium-Strong |
| Latency feasibility | ✅ Early signal |
| Real session-log intelligence | ❌ Weak (0.167 restore) |
| v2 ledger fields | ❌ Weak (~0.05) |
| Memory graph linkage | ❌ Weak (85% orphans) |
| Human correction loop | ❌ Not implemented |
| Live agent integration | ❌ Not implemented |

---

## Current RC4 Metrics

| Metric | Value | Gate | Status |
|--------|-------|------|--------|
| Tests passing | 84 | ≥80 | ✅ |
| Holdout restore | 1.000 | ≥0.80 | ✅ |
| Holdout recall | 0.717 | ≥0.60 | ✅ |
| Token avg | 69.5 | ≤120 | ✅ |
| PSO score | 0.650 | ≥0.50 | ✅ |
| Decision recall | 1.000 | ≥0.90 | ✅ |
| Error recall | 0.650 | ≥0.50 | ✅ |
| Query latency | 54ms | ≤200ms | ✅ |
| Ingestion rate | 20 mem/s | ≥5.0 | ✅ |

---

## RC4.5 — Signal Repair (Immediate)

**Goal:** Eliminate weak signals that are already visible in RC4 data.

### A. v2 Field Enrichment
- [ ] Add rationale/alternatives/tradeoffs to synthetic decision scenarios
- [ ] Add root_cause/fix_attempt/verified_fix/affected_files/recurrence_risk to error scenarios
- [ ] Target: Decision v2 ≥0.60, Error v2 ≥0.60

### B. Real Session-Log Intelligence
- [ ] Session-log goal extractor v2: detect "we need to...", "the goal is...", "let's fix..."
- [ ] Session-log error extractor v2: detect stack traces, test failures, type errors
- [ ] Intent-to-goal promotion when confidence is high
- [ ] Assistant-plan filtering: separate actual goals from speculation
- [ ] Session-log query rewriting: "What were the goals?" not "What is the state?"
- [ ] Target: real_session goal recall ≥0.60, error recall ≥0.60

### C. Memory Graph Health
- [ ] Auto-link memories during ingestion (not manual-only)
- [ ] Add link types: decision_affects_file, error_caused_by_symbol, etc.
- [ ] Orphan ratio gate: ≤40%
- [ ] Link audit CLI: `vcm inspect links <project_id>`

### D. PSO Maturity
- [ ] PSO field-level source pointers
- [ ] PSO delta log
- [ ] PSO conflict detector
- [ ] PSO from real session logs
- [ ] Target: PSO coverage ≥0.80

### E. Human Semantic Labels
- [ ] Complete or mark semantic precision as diagnostic-only

---

## RC5 — Self-Correcting Memory Runtime

**Goal:** Make the memory runtime self-correcting and usable in live agent workflows.

### A. Human-in-the-Loop Correction
- [ ] User memory correction API: mark stale/incorrect/important/duplicate
- [ ] Correction as training data for scorer/router
- [ ] Memory review queue for low-confidence items
- [ ] Contradiction resolution UI

### B. Pack Intelligence
- [ ] Pack sufficiency → auto-expand (rewrite query, re-retrieve)
- [ ] Streaming pack builder
- [ ] Retrieval router v3 with task-specific routes

### C. Cross-Project Intelligence
- [ ] Detect similar projects
- [ ] Transfer decisions/errors as warnings, not facts
- [ ] Embedding model upgrade experiment (BGE-small → BGE-base → Qwen3)

### D. Response Verifier v3
- [ ] Run verifier on actual agent responses in dogfooding
- [ ] Citation-to-memory validation
- [ ] Tool contradiction detection
- [ ] Auto-repair loop when verifier fails

---

## RC6 — Scale & Rich Modalities

**Goal:** Prepare memory OS for large projects and multimodal context.

### A. Scale
- [ ] Distributed storage (shard by project_id)
- [ ] PostgreSQL/pgvector or Qdrant migration path
- [ ] Load tests: 10k, 100k, 1M memories
- [ ] Multi-user isolation

### B. Multimodal
- [ ] Image/diagram indexing (OCR + vision embeddings)
- [ ] Code screenshot understanding
- [ ] Architecture diagram parsing

### C. Governance
- [ ] Memory export/delete API
- [ ] Tenant/project ACL
- [ ] Sensitive memory quarantine
- [ ] Production dashboard (health, latency, failures)

---

## v1.1 — Live Agent Integration

**Goal:** Transition from eval/runtime to real agent operation.

### A. Kimi Code CLI Full Loop
```text
before user query    → retrieve pack
after response       → verifier
after tool output    → ingest
after diff           → code index update
after tests          → error/PSO update
```

### B. End-to-End Benchmark
- [ ] Measure: correct next action, correct files touched, tests pass, no stale decisions
- [ ] Real long-session benchmark (not commit-derived)
- [ ] Verifier repair loop in live flow

### C. Continuous Eval
- [ ] Every PR: unit tests + regression + holdout + component evals + latency smoke
- [ ] Online evaluation: track real queries and ratings

---

## Definition of "Production-Ready" for V1.0

1. Real session-log restore ≥0.60
2. Goal/error extraction from real logs works
3. Decision v2 fields ≥0.60
4. Error v2 fields ≥0.60
5. PSO field coverage ≥0.80
6. Orphan ratio ≤40%
7. Secret redaction guaranteed before storage/embeddings
8. Verifier used in live loop (not just tests)
9. Kimi Code CLI calls VCM before/after agent steps
10. End-to-end coding task success measured
11. Large-store latency/load tests pass
12. Human correction API works
13. Memory dashboard usable
14. Strong baselines (RawVerbatim, StrongRAG) in every report

---

## Priority Execution Order

### This Sprint (RC4.5)
1. v2-field scenario enrichment
2. Session-log goal/error extractors
3. Auto memory linking
4. Orphan ratio gate

### Next Sprint (RC5 start)
5. Human correction API
6. Pack auto-expand
7. Verifier v3 on real responses
8. Cross-project transfer warnings

### Following Sprint (RC5 mid)
9. Streaming pack builder
10. Embedding model upgrade
11. PSO delta log and conflict detector

### Later (RC6)
12. Multimodal memories
13. Distributed storage
14. Production dashboard

---

## Files to Create/Modify

### New Files (RC4.5)
```
vcm_os/memory/writer/session_goal_extractor.py
vcm_os/memory/writer/session_error_extractor.py
vcm_os/memory/linker/auto_linker.py
vcm_os/memory/linker/link_types.py
vcm_os/memory/project_state/delta_log.py
vcm_os/memory/project_state/conflict_detector.py
scripts/enrich_v2_scenarios.py
tests/test_session_goal_extraction.py
tests/test_session_error_extraction.py
tests/test_auto_linker.py
tests/test_orphan_ratio.py
```

### Modified Files (RC4.5)
```
vcm_os/memory/writer/core.py           # auto-linking
vcm_os/memory/writer/extractor.py      # goal/error detection
vcm_os/memory/project_state/extractor.py  # source pointers
vcm_os/evals/scenarios/holdout_scenarios.py  # v2 fields
vcm_os/evals/scenarios/project_state_scenarios.py  # richer PSO
scripts/regression_suite.py            # orphan gate
```
