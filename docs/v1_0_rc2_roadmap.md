# VCM-OS v1.0 RC2 Roadmap

**Date:** 2026-05-10  
**Status:** Technology diagnosis + development map  
**Source:** User technology assessment document

---

## Current State Summary

VCM-OS is no longer an "idea for memory." It is a working prototype / release candidate with a full stack:

```
event-sourced memory
typed memory objects
session restore
decision/error ledgers
dense+sparse retrieval
RRF reranker
graph expansion
stale checker
decay
reflection
codebase index
verifier
eval harness
frozen holdout
component metrics
Project State Object
Exact Symbol Vault
RawVerbatim baseline
StrongRAG baseline
semantic matcher
trace/audit tooling
FastAPI server
CLI integration
```

**Current level:** `structured memory compiler + eval framework + baseline comparison + context pack compiler`

**Gap to full project:** `real long-session operation, reliable project-state memory, human-validated evaluation, production observability, multi-language indexing, learned routing, memory lifecycle governance`

---

## P0 — Mandatory Before Final v1.0

| # | Task | Why | Effort |
|---|------|-----|--------|
| 1 | **Human semantic validation** | Precision 0.200 — cannot be headline metric | High |
| 2 | **I01 Project State Restore ≥ 0.80** | Currently 0.667 — core "memory OS" claim | Medium |
| 3 | **Real codebase ≥ 20 scenarios** | Currently 3 — insufficient for real-world validation | High |
| 4 | **RawVerbatim/StrongRAG permanent baselines** | Without them, results are misleading | Low |
| 5 | **Full split manifest clarity** | Must define holdout_20, tuning_29, adversarial, etc. | Low |

---

## P1 — Technology Development (Next Sprint)

| # | Task | Why | Effort |
|---|------|-----|--------|
| 6 | **Decision Ledger v2 + rationale** | Most valuable after stale filter | Medium |
| 7 | **Error Ledger v2** | Large practical value for coding agents | Medium |
| 8 | **Multi-language code index** | Python-only is limiting | Medium |
| 9 | **Context Pack Builder v3** | Make it a true compiler | Medium |
| 10 | **Tool-result ingestion** | Memory must come from real agent actions | Medium |

---

## P2 — Research Leap

| # | Task | Why | Effort |
|---|------|-----|--------|
| 11 | **Learned retrieval router** | After accumulating trace data | High |
| 12 | **GraphRAG / Code graph** | For multi-hop reasoning | High |

---

## v1.0 RC2 Acceptance Gates

```text
1. I01 state restore >= 0.80
2. real-codebase scenarios >= 20
3. real-codebase restore >= 0.80
4. real task success >= 0.60
5. semantic precision >= 0.75 on human labels
6. exact symbol recall >= 0.95
7. stale rate <= 0.01
8. contamination <= 0.01
9. false canonical memory <= 0.02
10. tokens <= 70 average on holdout
11. p95 retrieval+pack latency measured
12. RawVerbatim+StrongRAG included in every report
```

---

## 50 Development Directions (10 Blocks)

### A. Project State & Session Continuity
1. Project State Object v2 (versioned state model)
2. Session Resume Protocol v2
3. Task Graph / TODO Graph
4. Branch-aware memory
5. Session fork/merge

### B. Decision, Rationale, and Stale Logic
6. Decision Ledger v2
7. Rationale Memory
8. Rejected Decision Guard
9. Stale Resolver v2
10. Decision Conflict UI / CLI

### C. Error, Debugging, and Failure Memory
11. Error Ledger v2
12. Verified Fix Registry
13. Failure Pattern Memory
14. Command Outcome Memory
15. Debugging Timeline

### D. Exact Symbols, Codebase, and Graph Memory
16. Exact Symbol Vault v2
17. Non-truncatable protected terms
18. Multi-language Code Indexer
19. Codebase Graph v2
20. Diff-aware Memory

### E. Raw Evidence and Retrieval Architecture
21. Raw Evidence Layer
22. RawVerbatim fallback inside VCM
23. Retrieval Router v2
24. Learned Retrieval Router
25. Retrieval Attribution

### F. Context Pack Compiler
26. Context Pack Builder v3 (slot-based compiler)
27. Budget Optimizer
28. Pack Sufficiency Verifier v2
29. Multi-pack Mode
30. Context Pack Cache

### G. Evaluation and Metrics
31. Human-validated Semantic Eval
32. Real Long-Session Benchmark
33. Real Codebase Dogfooding v2
34. Strong Baseline Suite (permanent)
35. End-to-End Coding Task Eval

### H. Production, Safety, and Governance
36. Secret / PII Redaction
37. Memory Access Control
38. Memory Retention Policies v2
39. Memory Quarantine
40. Memory Audit Dashboard

### I. Agent Runtime Integration
41. Kimi Code CLI Adapter v2
42. Tool Result Ingestion
43. Agent Action Verifier
44. Memory Update After Patch
45. Procedural Memory

### J. Advanced / Research-Level Improvements
46. Multi-Agent Memory Manager
47. GraphRAG Integration
48. Learned Importance Scoring
49. Memory Simulation / Replay
50. Continual Memory Benchmark Generator

---

## Strategic Conclusion

**Current:** `VCM-OS as a compact structured memory compiler`

**Next:** `VCM-OS as an operational memory runtime for coding agents`

Four big layers to close:
1. Project-state reliability
2. Real-codebase workflow
3. Rationale/error/procedure memory
4. Production governance and observability

**Next sprint focus:**
```text
- PSO v2
- Decision Ledger v2
- Error Ledger v2
- Tool-result ingestion
- Real dogfooding harness
- Human semantic validation
```
