# VCM-OS Roadmap v1.0 — Live Runtime Alpha → Production

**Date:** 2026-05-12  
**Status:** Architecture vision + implementation plan  
**Based on:** RC5 complete (116/116 tests, 10/10 gates), ready for live integration

---

## 1. Главный вердикт

VCM-OS уже решает реальную проблему: агенту не нужно тащить всю историю в prompt.

Но ещё не доказана вторая вещь: что в живом coding workflow он стабильно повышает качество работы агента лучше, чем RawVerbatim, StrongRAG или большой context window.

VCM-OS — это ранний **memory runtime**, не просто RAG:

```
event log → typed memories → linked memory graph → project state
→ decision/error ledgers → exact symbol vault → retrieval/router
→ compact verified pack → verifier → repair loop → correction API → tool ingestion
```

---

## 2. Сильные стороны (уже реализовано)

| Компонент | Статус | Ключевой результат |
|-----------|--------|-------------------|
| Memory core | ✅ | Event-sourced typed memory, SQLite, vector+sparse, RRF |
| Verifier v2 | ✅ | 10 checks, repair loop |
| Secret redaction | ✅ | 7 patterns, 0 false negatives |
| Human correction API | ✅ | 7 actions, review queue, audit log |
| Pack auto-expand | ✅ | Query rewrite + re-retrieve, max 2 iter |
| Baselines | ✅ | RawVerbatim, StrongRAG, Summary, FullContext |
| Auto-linker | ✅ | 85% → 0% orphans |
| Health dashboard | ✅ | 10 metrics + overall score |
| Production dashboard | ✅ | CLI + 5 API endpoints |
| E2E benchmark | ✅ | 3 tasks, framework ready |

---

## 3. Главные слабые точки

| # | Проблема | Почему критично |
|---|----------|----------------|
| 1 | **Live agent integration отсутствует** | VCM — backend-библиотека, не память агента |
| 2 | **E2E benchmark слабый** | 3 tasks, avg_score 0.47, cache_migration = -0.2 |
| 3 | **Real session-log restore слабый** | 0.167 restore, 0.000 goals/errors |
| 4 | **Ingestion bottleneck** | 4.3 mem/s, embedding dominates |
| 5 | **SQLite single-node** | Нет production backend |
| 6 | **Link quality неизвестна** | Orphan=0%, но precision/recall не измерены |
| 7 | **Action value не доказана** | Restore высокий, но реальный агент может кодить не лучше |

---

## 4. Целевая архитектура

```
┌─────────────────────────────────────┐
│  IDE / CLI / Agent Client           │
│  VS Code / Kimi CLI / Codex CLI     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  VCM Agent Gateway                  │
│  - session detection                │
│  - before-query pack retrieval      │
│  - after-response verification      │
│  - repair loop                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  VCM Runtime API                    │
│  /events /context/build /verify     │
│  /memory/search /corrections        │
│  /projects/{id}/state               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Memory Core                        │
│  Event Log → Typed Memories         │
│  Decision/Error Ledgers → PSO       │
│  Symbol Vault → Raw Evidence        │
│  Links/Graph                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Storage                            │
│  SQLite local / Postgres+pgvector   │
│  Vector backend optional            │
│  Sparse backend optional            │
└─────────────────────────────────────┘
```

---

## 5. План интеграции (5 режимов)

### 5.1. Local sidecar server
```bash
vcm serve --project ./my-app  # localhost:8123
```

### 5.2. MCP server
Tools: `vcm_build_context`, `vcm_write_event`, `vcm_verify_response`, `vcm_search_memory`, `vcm_correct_memory`, `vcm_get_project_state`

### 5.3. LLM proxy / gateway
```
client → VCM Gateway → LLM API
```
Gateway автоматически: определяет project/session, строит pack, добавляет к prompt, проверяет ответ, сохраняет событие.

### 5.4. VS Code extension
Memory panel: active decisions, stale warnings, exact symbols, corrections.

### 5.5. CLI wrapper
```bash
vcm run kimi-code
vcm run codex
```
Перехватывает user/assistant/tool/git/test events.

---

## 6. Формулы системы

### 6.1. Экономия токенов
```
T_full(n) = T_system + Σ history_i + T_current
T_vcm(n)  = T_system + T_recent + T_pack + T_current
Savings   = 1 - T_vcm / T_full
```
Для 100 сообщений: T_full ≈ 50k, T_vcm ≈ 2.5k–5k → Savings 90–95%.

### 6.2. Retrieval score
```
Score(m, q) =
  0.30 · dense_similarity
+ 0.20 · bm25_score
+ 0.25 · exact_symbol_match
+ 0.05 · recency
+ 0.10 · status_score
+ 0.05 · graph_relevance
+ 0.10 · project_scope_match
- 0.40 · stale_penalty
- 1.00 · wrong_project_penalty
- 0.10 · duplication_penalty
```

### 6.3. Pack sufficiency
```
Sufficiency =
  0.18 · goal_coverage
+ 0.18 · decision_coverage
+ 0.14 · error_coverage
+ 0.14 · exact_symbol_coverage
+ 0.12 · file_reference_coverage
+ 0.10 · tool_evidence_coverage
+ 0.08 · rationale_coverage
+ 0.06 · citation_coverage
- 0.20 · stale_conflict_penalty
```
Thresholds: S ≥ 0.85 sufficient, 0.65–0.85 auto-expand, < 0.65 ask for more.

### 6.4. Dynamic pack budget
```
B_pack = clamp(
  B_base(task)
  + 120 · missing_critical_types
  + 80  · exact_symbol_count
  + 150 · stale_conflict_count
  + 200 · multi_file_complexity
  + 250 · debugging_flag
  + 300 · architecture_flag,
  B_min, B_max
)
```
Suggested: simple=100–150, normal=300–500, debug=700–1200, refactor=1000–2000, architecture=2000–5000.

### 6.5. Memory importance
```
Importance(m) =
  0.20 · user_explicitness
+ 0.20 · affects_code
+ 0.15 · decision_value
+ 0.15 · error_value
+ 0.10 · recurrence_risk
+ 0.10 · exact_symbol_density
+ 0.05 · future_task_relevance
+ 0.05 · security_relevance
```

### 6.6. Runtime health score
```
Health =
  0.20 · (1 - stale_leak_rate)
+ 0.15 · (1 - orphan_ratio)
+ 0.15 · (1 - duplicate_ratio)
+ 0.15 · verifier_pass_rate
+ 0.10 · redaction_pass_rate
+ 0.10 · link_precision
+ 0.10 · latency_score
+ 0.05 · correction_resolution_rate
```

### 6.7. Link confidence
```
LinkScore(a, b) =
  0.25 · shared_symbols
+ 0.20 · shared_files
+ 0.20 · temporal_proximity
+ 0.15 · semantic_similarity
+ 0.10 · same_session
+ 0.10 · explicit_reference
```
≥0.80 strong, 0.55–0.80 weak, <0.55 no link.

---

## 7. Карта развития: 50 задач

| # | Задача | Как проверить | Приоритет |
|---|--------|---------------|-----------|
| 1 | Live Kimi/agent integration | 10 live sessions, VCM vs no-VCM | 🔴 P0 |
| 2 | LLM proxy gateway | Prompt contains pack, verifier runs | 🔴 P0 |
| 3 | MCP server | Agent calls tools | 🔴 P0 |
| 4 | VS Code extension | Memory panel works | 🟡 P1 |
| 5 | CLI wrapper `vcm run` | Events auto-captured | 🔴 P0 |
| 6 | Real session-log extractor v3 | restore 0.167 → ≥0.60 | 🟡 P1 |
| 7 | Intent-to-goal promotion | goal recall improves | 🟡 P1 |
| 8 | Assistant speculation filter | false canonical ≤2% | 🟡 P1 |
| 9 | Temporary vs accepted plan classifier | proposed→active after evidence | 🟡 P1 |
| 10 | User correction detector | repeated correction rate drops | 🟡 P1 |
| 11 | E2E benchmark 30 tasks | avg_score ≥0.65 | 🔴 P0 |
| 12 | Fix cache_migration failure | no negative task class | 🔴 P0 |
| 13 | 100-message web-app benchmark | budget curve vs baselines | 🟡 P1 |
| 14 | Long-break resume (24h/72h/7d) | correct next action ≥0.75 | 🟡 P1 |
| 15 | Step-20 recovery at step 100 | VCM finds rationale and files | 🟡 P1 |
| 16 | Dynamic budget policy | quality/token sweet spot | 🟡 P1 |
| 17 | Pack sufficiency v2 | missing critical ≤5% | 🟡 P1 |
| 18 | Auto-expand repair | verifier failures drop | 🟡 P1 |
| 19 | Response verifier v3 | catches seeded violations | 🟡 P1 |
| 20 | Verifier repair loop live | repair success ≥70% | 🟡 P1 |
| 21 | Raw evidence fallback | improves real-session restore | 🟡 P1 |
| 22 | Decision Ledger v3 | decision correctness ≥0.90 | 🟢 P2 |
| 23 | Rationale memory type | rationale recall ≥0.75 | 🟢 P2 |
| 24 | Rejected idea guard | revival rate ≤2% | 🟢 P2 |
| 25 | Stale resolver v3 | stale leak ≤1% | 🟢 P2 |
| 26 | Error Ledger v3 | repeated bug fix time drops | 🟢 P2 |
| 27 | Debug timeline | root cause restore ≥0.80 | 🟢 P2 |
| 28 | Tool trust scoring | tool contradiction drops | 🟢 P2 |
| 29 | Tool parser expansion | per-tool coverage tests | 🟢 P2 |
| 30 | Git diff memory | code-memory drift ≤5% | 🟡 P1 |
| 31 | Tree-sitter code index | symbol precision ≥0.90 | 🟢 P2 |
| 32 | Code graph v2 | multi-hop code QA ≥0.75 | 🟢 P2 |
| 33 | Symbol Vault v3 | protected symbol recall ≥0.95 | 🟢 P2 |
| 34 | Non-truncatable symbols | 0 critical truncations | 🟢 P2 |
| 35 | Symbol collision resolver | cross-repo contamination ≤1% | 🟢 P2 |
| 36 | Link quality eval | precision ≥0.80 | 🟡 P1 |
| 37 | Memory graph audit | dashboard graph health | 🟢 P2 |
| 38 | Human semantic validation | precision ≥0.75, recall ≥0.80 | 🟡 P1 |
| 39 | Partial-match scoring | honest semantic metric | 🟢 P2 |
| 40 | Strong baseline suite permanent | every report has baselines | 🟡 P1 |
| 41 | Batch embeddings | ingestion ≥20 mem/s | 🟡 P1 |
| 42 | Async ingestion queue | write latency <50ms | 🟡 P1 |
| 43 | Embedding cache | ingestion cost drops | 🟢 P2 |
| 44 | Incremental health snapshot | health <200ms at 20k | 🟡 P1 |
| 45 | Large-store load (100k/1M) | query p95 <250ms at 100k | 🟢 P2 |
| 46 | Postgres/pgvector backend | migration tests pass | 🟢 P2 |
| 47 | Qdrant/Milvus backend | recall parity | 🟢 P2 |
| 48 | Security governance | no secret leakage | 🟡 P1 |
| 49 | Production dashboard web UI | operator can debug | 🟢 P2 |
| 50 | Multimodal memory | image evidence retrievable | 🟢 P2 |

---

## 8. Необходимые эксперименты

### 8.1. Token budget curve
Budgets: 70, 150, 300, 500, 1000, 1500, 3000. Baselines: Full, RawVerbatim, StrongRAG, Last-N. Tasks: simple, debug, refactor, architecture, resume.

Expected: 70 for state reminders, 300–500 for normal coding, 700–1500 for debug/refactor.

### 8.2. VCM vs RawVerbatim live test
30 live coding sessions. VCM must beat RawVerbatim on stale suppression, decision correctness, task success.

### 8.3. Real session-log extraction
100 real logs. Goal: goal recall ≥0.70, error recall ≥0.70, false active decision ≤2%.

### 8.4. Link quality benchmark
Manual gold links for 500 pairs. Goal: precision ≥0.80, recall ≥0.60, wrong_link ≤5%.

### 8.5. End-to-end coding tasks
30–100 tasks: auth, cache migration, schema migration, API versioning, CI failure, security patch, dependency conflict, test flake, deployment rollback, feature flag.

```
TaskScore =
  0.30 · tests_pass
+ 0.20 · correct_files
+ 0.15 · decision_constraints_followed
+ 0.15 · error_fixed
+ 0.10 · no_stale_usage
+ 0.10 · verifier_pass
```

Pass: avg ≥0.65 first, ≥0.80 mature, no negative task class.

### 8.6. Long-context degradation comparison
Compare: Full 50k, Full 100k, VCM 500, VCM 1000, RawVerbatim, StrongRAG. Goal: prove VCM retains state with less context and less noise.

---

## 9. Public API (v1)

```http
POST /v1/events
POST /v1/context/build
POST /v1/verify
POST /v1/memory/search
POST /v1/memory/correct
GET  /v1/projects/{id}/state
GET  /v1/projects/{id}/decisions
GET  /v1/projects/{id}/errors
GET  /v1/projects/{id}/symbols
GET  /v1/health
```

### Context build request
```json
{
  "project_id": "proj_webapp",
  "session_id": "sess_123",
  "query": "Continue fixing cache migration",
  "task_type": "debugging",
  "budget": {"mode": "auto", "max_tokens": 1000},
  "include": {
    "project_state": true,
    "decisions": true,
    "errors": true,
    "symbols": true,
    "tool_evidence": true,
    "raw_fallback": true
  }
}
```

### Context response
```json
{
  "pack_text": "...",
  "token_estimate": 742,
  "sufficiency_score": 0.91,
  "sections": {
    "project_state": [],
    "active_decisions": [],
    "errors": [],
    "symbols": [],
    "tool_evidence": [],
    "stale_warnings": []
  },
  "trace": {
    "retrieved": [],
    "included": [],
    "dropped": [],
    "drop_reasons": []
  }
}
```

---

## 10. Acceptance criteria для "полноценного проекта"

1. Live agent integration works in real CLI/IDE workflow.
2. Real session-log restore ≥0.70.
3. E2E coding benchmark avg_score ≥0.70.
4. No task class has negative average score.
5. VCM beats RawVerbatim on stale suppression, decision correctness, task success.
6. VCM beats StrongRAG or matches with fewer tokens on real tasks.
7. Dynamic budget curve measured and documented.
8. Human semantic validation precision ≥0.75.
9. Link precision ≥0.80.
10. Secret redaction false negatives = 0 on seeded suite.
11. Query p95 <150ms at 20k memories.
12. Ingestion ≥20 mem/s at 20k memories.
13. Health snapshot <500ms at 100k memories.
14. Production storage backend beyond SQLite.
15. VS Code/CLI/MCP integration usable by non-experts.

---

## 11. Что делать прямо сейчас — "Live Runtime Alpha"

Фокус на 10 deliverables:

1. **VCM Gateway / proxy** — перехватывать запросы, вставлять pack
2. **MCP server** — expose tools для агентов
3. **Kimi Code CLI wrapper** — `vcm run kimi-code`
4. **VS Code extension skeleton** — memory panel
5. **Live ingestion** — user/assistant/tool/git/test events
6. **Verifier repair loop in live workflow** — проверять ответы
7. **30 live coding sessions** — собрать реальные данные
8. **E2E benchmark expansion** — 3 → 30 tasks
9. **Token budget curve experiment** — найти sweet spot
10. **Trace dashboard** — debug failed tasks

**Success criteria для Alpha:**
- real_session_restore ≥0.50
- e2e avg_score ≥0.60
- cache_migration no longer negative
- no secret leakage
- stale violation ≤2%
- VCM better than RawVerbatim on decision/stale

---

## 12. Финальное видение

VCM-OS — операционная система памяти для AI-разработчика.

Пользователь не думает:
- какой контекст вставить?
- что агент забыл?
- можно ли доверять ответу?
- не использовал ли агент старое решение?

VCM-OS автоматически:
- запоминает важное
- выкидывает шум
- связывает решение с ошибкой и файлом
- сохраняет exact symbols
- показывает агенту только нужное
- проверяет ответ
- записывает tool results
- принимает correction
- не раскрывает секреты

Ключевая формула:
```
Context window = рабочая область
VCM-OS = долговременная память проекта
Files/tools = источник деталей
Verifier = защита от неправильного использования памяти
Correction API = способ памяти учиться от пользователя
```

Самая важная следующая проверка:
> Может ли агент через 100 сообщений и 3 дня продолжить реальный проект лучше, дешевле и безопаснее, чем без VCM?
