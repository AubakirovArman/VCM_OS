# VCM-OS Development Roadmap

Дата фиксации: 2026-05-14  
Основано на статусе runtime-core от 2026-05-12.

## Главный Вердикт

VCM-OS уже является ранним memory runtime для coding agents, а не очередным RAG. Система хранит проектную память как typed, stale-aware, project-scoped state и строит минимальный проверяемый context pack для текущей задачи.

Текущая сильная формула:

```text
project events/tools/code/session
→ typed/stale-aware/project-scoped memory
→ compact verified pack
→ answer verification
→ memory correction/update
```

Следующее доказательство должно быть не только restore/gates, а live coding value:

```text
Может ли агент через 100 сообщений и 3 дня продолжить реальный проект лучше,
дешевле и безопаснее, чем без VCM?
```

## Что Уже Сильно

- Event-sourced typed memory: decisions, errors, goals, code changes, facts, tool output, tasks.
- SQLite metadata + dense vector index + BM25 sparse index.
- RRF fusion retrieval and task-aware routing.
- Compact context pack builder with adaptive compression.
- Response verifier: stale facts, rejected decisions, active-decision contradictions, tool evidence mismatch, unverified files/symbols, unsupported claims, missing citations.
- Secret redaction before storage and indexing.
- Human correction API: stale, incorrect, important, duplicate, pin, unpin, delete.
- Pack sufficiency auto-expand and repair loop.
- Auto-linker and linked memory graph.
- Strong baselines: Full, Summary, RAG, RawVerbatim, StrongRAG.

## Главные Риски

1. Live agent integration is still the main product gap. VCM must sit inside the user/assistant/tool loop.
2. Real session logs are noisy. Earlier session-log restore was weak and needs v3 extraction.
3. E2E coding success matters more than component tests.
4. Ingestion throughput and health snapshots need scale work.
5. SQLite is correct for local-first, but production needs a storage migration path.
6. Link quality must be measured. Orphan ratio alone is not enough.
7. VCM must prove action value, not just high restore.

## Целевая Архитектура

```text
IDE / CLI / Agent Client
  VS Code / Kimi CLI / Codex CLI
        ↓
VCM Agent Gateway
  session detection
  before-query pack retrieval
  after-response verification
  repair loop
        ↓
VCM Runtime API
  /events
  /context/build
  /verify
  /memory/search
  /memory/correct
  /projects/{id}/state
        ↓
Memory Core
  event log
  typed memories
  decision/error ledgers
  project state object
  exact symbol vault
  raw evidence
  links/graph
        ↓
Storage
  SQLite local
  Postgres/pgvector production option
  optional vector/sparse/graph backends
```

## Product Modes

### Local Sidecar

```bash
vcm serve --project ./my-app
```

Local sidecar is the default private workflow: agent clients call `localhost:8123` for context, verification, and event writes.

### MCP Server

Required tools:

```text
vcm_build_context
vcm_write_event
vcm_verify_response
vcm_search_memory
vcm_correct_memory
vcm_get_project_state
```

### LLM Gateway

```text
client → VCM Gateway → LLM API
```

Gateway responsibilities:

```text
1. detect project/session
2. build memory pack
3. inject pack into prompt
4. forward request to LLM
5. verify response
6. persist user/assistant events
```

### VS Code Extension

The extension should expose memory as product UI, not as ML internals:

```text
Memory panel
active decisions
stale warnings
git/tool capture
corrections
why-this-memory trace
```

### CLI Wrapper

```bash
vcm run kimi-code
vcm run codex
vcm run my-agent
```

Wrapper should capture user messages, assistant responses, tool outputs, git diffs, and test results.

## Core Formulas

### Token Savings

```text
T_full(n) = T_system + sum(history_i) + T_current
T_vcm(n)  = T_system + T_recent + T_pack + T_current
Savings   = 1 - T_vcm / T_full
Ratio     = T_full / T_vcm
```

For a 100-message coding session:

```text
T_full ≈ 50,000
T_vcm  ≈ 2,500-5,000
Savings ≈ 90%-95%
Ratio ≈ 10x-20x
```

### Retrieval Score

```text
Score(m, q) =
  0.30 * dense_similarity(m, q)
+ 0.20 * bm25_score(m, q)
+ 0.25 * exact_symbol_match(m, q)
+ 0.05 * recency(m)
+ 0.10 * status_score(m)
+ 0.05 * graph_relevance(m, q)
+ 0.10 * project_scope_match(m)
- 0.40 * stale_penalty(m)
- 1.00 * wrong_project_penalty(m)
- 0.10 * duplication_penalty(m)
```

### Pack Sufficiency

```text
Sufficiency =
  0.18 * goal_coverage
+ 0.18 * decision_coverage
+ 0.14 * error_coverage
+ 0.14 * exact_symbol_coverage
+ 0.12 * file_reference_coverage
+ 0.10 * tool_evidence_coverage
+ 0.08 * rationale_coverage
+ 0.06 * citation_coverage
- 0.20 * stale_conflict_penalty
```

Thresholds:

```text
S >= 0.85        sufficient
0.65 <= S < 0.85 auto-expand
S < 0.65         retrieve raw evidence or ask for more context
```

### Dynamic Pack Budget

```text
B_pack =
  clamp(
    B_base(task)
  + 120 * missing_critical_types
  + 80  * exact_symbol_count
  + 150 * stale_conflict_count
  + 200 * multi_file_complexity
  + 250 * debugging_flag
  + 300 * architecture_flag,
    B_min,
    B_max
  )
```

Suggested budgets:

```text
simple continuation: 100-150
normal coding:       300-500
debugging:           700-1200
multi-file refactor: 1000-2000
architecture/audit:  2000-5000
```

### Memory Importance

```text
Importance(m) =
  0.20 * user_explicitness
+ 0.20 * affects_code
+ 0.15 * decision_value
+ 0.15 * error_value
+ 0.10 * recurrence_risk
+ 0.10 * exact_symbol_density
+ 0.05 * future_task_relevance
+ 0.05 * security_or_privacy_relevance
```

### Link Confidence

```text
LinkScore(a, b) =
  0.25 * shared_symbols
+ 0.20 * shared_files
+ 0.20 * temporal_proximity
+ 0.15 * semantic_similarity
+ 0.10 * same_session
+ 0.10 * explicit_reference
```

Thresholds:

```text
>= 0.80 strong link
0.55-0.80 weak link
< 0.55 no link
```

### Runtime Health

```text
Health =
  0.20 * (1 - stale_leak_rate)
+ 0.15 * (1 - orphan_ratio)
+ 0.15 * (1 - duplicate_ratio)
+ 0.15 * verifier_pass_rate
+ 0.10 * redaction_pass_rate
+ 0.10 * link_precision
+ 0.10 * latency_score
+ 0.05 * correction_resolution_rate
```

## Backlog By Track

### Live Integration

1. Live Kimi/agent integration before every agent request.
2. LLM proxy gateway with memory injection and response verification.
3. MCP server hardening for build/write/verify/search/correct/state.
4. VS Code memory panel with correction UI.
5. CLI wrapper that captures events, tools, git diffs, and tests.
6. Verifier repair loop wired into live responses.

### Extraction And Memory Quality

1. Real session-log extractor v3 for noisy coding transcripts.
2. Intent-to-goal promotion with false-positive protection.
3. Assistant speculation filter.
4. Temporary vs accepted plan classifier.
5. User correction detector that updates memory automatically.
6. Raw evidence fallback when structured memory is weak.

### Evals

1. 30-100 end-to-end coding tasks.
2. 100-message web-app benchmark.
3. Long-break resume benchmark for 24h, 72h, 7d.
4. Step-20 recovery test: decision at step 20 needed at step 100.
5. Token budget curve: 70, 150, 300, 500, 1000, 1500, 3000.
6. VCM vs Full, Last-N, RawVerbatim, StrongRAG, Summary on every report.
7. Human semantic validation for goal/decision pairs.
8. Link quality benchmark with manual gold labels.

### Ledgers And Verification

1. Decision Ledger v3: lifecycle, rationale, affected files, owner, confidence.
2. Rationale memory type for why/alternatives/tradeoffs.
3. Rejected idea guard to prevent old rejected ideas from resurfacing.
4. Stale resolver v3 that preserves history while blocking stale use.
5. Error Ledger v3: root cause, failed fixes, verified fix, recurrence risk.
6. Debug timeline: symptom → hypothesis → command → fix.
7. Tool trust scoring: tool output beats assistant claim.
8. Response Verifier v3 with stronger citations, files, tools, stale, and symbols.

### Code Intelligence

1. Tool parser expansion for pytest, npm, cargo, docker, k8s, terraform, security scanners.
2. Git diff memory that updates changed files/symbols.
3. Tree-sitter code index to replace regex parsing where precision matters.
4. Code graph v2: file → symbol → test → decision links.
5. Symbol Vault v3 for DB tables, migrations, k8s resources, tests, branches.
6. Non-truncatable protected symbols.
7. Symbol collision resolver across repos and projects.

### Scale And Production

1. Batch embeddings.
2. Async ingestion queue.
3. Embedding cache.
4. Incremental health snapshot.
5. Load tests at 100k and 1M memories.
6. Postgres/pgvector backend.
7. Optional Qdrant/Milvus backend.
8. Security governance: access control, export/delete, redaction audit.
9. Production dashboard for memory health and traces.
10. Multimodal memory for screenshots, diagrams, and UI evidence.

## Required Experiments

### Token Budget Curve

Run VCM packs at:

```text
70, 150, 300, 500, 1000, 1500, 3000 tokens
```

Measure:

```text
task_success
decision_correctness
rationale_recall
exact_symbol_recall
stale_violation
tokens
latency
```

Expected:

```text
70       simple state reminders
300-500  normal coding
700-1500 debugging/refactor
```

### Live VCM Vs RawVerbatim

Run 30 live coding sessions replayed with:

```text
no memory
RawVerbatim
StrongRAG
VCM
```

Pass condition:

```text
VCM beats RawVerbatim on stale suppression, decision correctness, and task success.
```

### Real Session-Log Extraction

Run 100 real logs.

Pass targets:

```text
goal recall >= 0.70
error recall >= 0.70
false active decision <= 0.02
```

### End-To-End Coding Tasks

Task score:

```text
TaskScore =
  0.30 * tests_pass
+ 0.20 * correct_files
+ 0.15 * decision_constraints_followed
+ 0.15 * error_fixed
+ 0.10 * no_stale_usage
+ 0.10 * verifier_pass
```

Targets:

```text
first mature gate: avg_score >= 0.65
later mature gate: avg_score >= 0.80
no negative task class
```

## Public API Target

```http
POST /v1/events
POST /v1/context/build
POST /v1/verify
POST /v1/memory/search
POST /v1/memory/correct
GET  /v1/projects/{project_id}/state
GET  /v1/projects/{project_id}/decisions
GET  /v1/projects/{project_id}/errors
GET  /v1/projects/{project_id}/symbols
GET  /v1/health
```

## Acceptance Criteria

VCM-OS is a complete product when:

```text
1. Live agent integration works in real CLI/IDE workflows.
2. Real session-log restore >= 0.70.
3. E2E coding benchmark avg_score >= 0.70.
4. No task class has negative average score.
5. VCM beats RawVerbatim on stale suppression, decision correctness, and task success.
6. VCM matches or beats StrongRAG with materially fewer tokens on real tasks.
7. Dynamic budget curve is measured and documented.
8. Human semantic validation precision >= 0.75.
9. Link precision >= 0.80.
10. Secret redaction false negatives = 0 on seeded suite.
11. Query p95 < 150ms at 20k memories.
12. Ingestion >= 20 mem/s at 20k memories.
13. Health snapshot < 500ms at 100k memories.
14. Production storage backend exists beyond SQLite.
15. VS Code, CLI, and MCP integration are usable by non-experts.
```

## Immediate Sprint: Live Runtime Alpha

Deliverables:

```text
1. Harden VCM Gateway / proxy.
2. Harden MCP server.
3. Harden Kimi Code CLI wrapper.
4. Expand VS Code extension skeleton into usable memory panel.
5. Live ingestion of user/assistant/tool/git/test events.
6. Verifier repair loop inside live workflow.
7. 30 live coding sessions.
8. E2E benchmark expanded and tracked.
9. Token budget curve experiment.
10. Trace dashboard for failed tasks.
```

First success targets:

```text
real_session_restore >= 0.50
e2e avg_score >= 0.60
cache_migration no longer negative
no secret leakage
stale violation <= 0.02
VCM better than RawVerbatim on decision/stale metrics
```

