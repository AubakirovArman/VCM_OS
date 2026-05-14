# VCM-OS "Live Runtime Alpha" — Complete Summary

**Date:** 2026-05-12  
**Sprint:** Live Runtime Alpha (10 tasks)  
**Status:** ALL COMPLETE  

---

## Executive Summary

VCM-OS прошёл от "backend-библиотеки" до "работающего runtime с gateway, CLI и 30-task benchmark".  
Ключевой результат: **E2E benchmark avg score 0.90** (было 0.47), **25/30 задач проходят**.

---

## What Was Built

### 1. Dynamic Pack Budget (Token Curve)

**Problem:** Hard cap 65 tokens truncated critical keywords (cache_migration scored −0.2).

**Solution:**
- Added `max_pack_tokens` to `MemoryRequest` (default 65, configurable)
- Dynamic per-item cap: `cap = base_cap * min(5, max_pack_tokens / 100)`
- Dynamic max_items: `max_items + (max_pack_tokens - 150) / 100`

**Results:**

| Budget | Avg Score | Avg Recall | Avg Tokens |
|--------|-----------|------------|------------|
| 70     | 0.72      | 0.80       | 60         |
| 150    | 0.82      | 0.90       | 64         |
| 300    | 0.85      | 0.93       | 70         |
| **500**| **0.92**  | **1.00**   | **75**     |
| 1000+  | 0.92      | 1.00       | 75         |

**Key insight:** 500 tokens is the sweet spot for current task complexity.

**Files changed:**
- `vcm_os/schemas/context.py` — `max_pack_tokens: int = 65`
- `vcm_os/context/pack_builder/core.py` — dynamic cap/max_items
- `vcm_os/context/pack_builder/assembler.py` — pass `request` to `_build_section`
- `vcm_os/context/pack_builder/compact_assembler.py` — pass `request` to `_build_section`

---

### 2. VCM Gateway / LLM Proxy

**What:** OpenAI-compatible proxy that injects VCM memory pack into system prompt.

**Flow:**
```
Client → /gateway/chat/completions
  ↓
Extract query → Build VCM pack → Inject into system prompt
  ↓
Forward to LLM API (localhost:8000)
  ↓
Receive response → Verify → Persist → Return with VCM metadata
```

**Headers:**
- `x-project-id` — required
- `x-session-id` — optional
- `x-vcm-budget` — pack token limit (default 500)

**Tested with:** Gemma 4 31B via vLLM  
**Result:** Query "What database?" → Response "PostgreSQL" using pack  
**Prompt tokens:** 90 (includes VCM pack)

**VCM metadata in response:**
```json
{
  "vcm": {
    "pack_sufficiency": 0.7,
    "pack_tokens": 40,
    "verifier_passed": true,
    "verifier_score": 1.0
  }
}
```

**File:** `vcm_os/app/routers/gateway.py`

---

### 3. CLI Wrapper (`vcm`)

**7 subcommands:**

| Command | What it does |
|---------|-------------|
| `vcm serve [--port]` | Start API server |
| `vcm run <command>` | Run command with stdout capture |
| `vcm ingest <file>` | Ingest file into memory |
| `vcm ingest-git` | Auto-ingest `git diff` + `git status` |
| `vcm status` | Show project memory stats |
| `vcm memory search <query>` | Search memories |
| `vcm memory correct <id> <action>` | Apply correction |
| `vcm benchmark [--suite]` | Run benchmark suite |

**Examples:**
```bash
python scripts/vcm status
python scripts/vcm memory search "database"
python scripts/vcm ingest-git
python scripts/vcm run pytest
```

**File:** `scripts/vcm` (executable)

---

### 4. E2E Benchmark v2 (30 Tasks)

**10 categories × 3 tasks = 30 coding scenarios:**

| Category | Tasks | Avg Score | Pass Rate |
|----------|-------|-----------|-----------|
| Auth | 3 | 0.77 | 2/3 |
| Cache | 3 | 0.93 | 3/3 |
| Database | 3 | 0.97 | 3/3 |
| API | 3 | 0.93 | 3/3 |
| Testing | 3 | 0.90 | 3/3 |
| Deployment | 3 | 1.00 | 3/3 |
| Error Handling | 3 | 0.80 | 2/3 |
| Refactoring | 3 | 1.00 | 3/3 |
| Architecture | 3 | 0.92 | 2/3 |
| Debugging | 3 | 0.75 | 1/3 |

**Overall:**
- **Passed (≥0.8):** 25/30
- **Avg Score:** 0.90 (was 0.47)
- **Avg Recall:** 0.94
- **Avg Latency:** 43.8ms

**Weak tasks (need attention):**
- `auth_rbac` — 0.50 (missing role keywords in pack)
- `error_retries` — 0.50 ("tenacity" not found)
- `debug_race_condition` — 0.50 ("UUID7" not found)
- `arch_event_driven` — 0.75 ("RabbitMQ" found, not enough context)
- `debug_memory_leak` — 0.75 (truncation cuts key details)

**File:** `scripts/e2e_benchmark_v2.py`

---

### 5. Embedding Optimization

**Problem:** Ingestion at 4.3 mem/s — embedding dominates.

**Fix:** `functools.lru_cache(maxsize=4096)` on `VectorIndex.encode()`.

**Impact:** Repeated texts (duplicates, similar events) skip recomputation.

**File:** `vcm_os/storage/vector_index.py`

---

### 6. Incremental Health Snapshot

**Problem:** Health snapshot took 1.9s at 20k memories (full table scans).

**Fix:** 60-second TTL cache in `MemoryHealthDashboard`.

**Behavior:**
- First call: computes full snapshot
- Subsequent calls within 60s: returns cached result with `cache_age_seconds`

**File:** `vcm_os/health/dashboard.py`

---

### 7. Link Quality Evaluation

**Heuristic evaluation** (no human gold labels):

| Metric | Value |
|--------|-------|
| Total memories | 941 |
| Total links | 359 |
| **Precision (≥2 signals)** | **0.903** |
| `shared_file` precision | 0.933 |
| `same_session` precision | 0.689 |

**Observation:** Shared-file links are highly precise. Same-session links are noisier (many weak connections).

**File:** `scripts/link_quality_eval.py`

---

### 8. MCP Server

**6 tools exposed via FastMCP:**

| Tool | Purpose |
|------|---------|
| `vcm_build_context` | Build memory pack for query |
| `vcm_write_event` | Ingest event into memory |
| `vcm_verify_response` | Verify assistant response |
| `vcm_search_memory` | Search project memory |
| `vcm_correct_memory` | Apply memory correction |
| `vcm_get_project_state` | Get active decisions/errors/goals |

**Usage:** Any MCP-compatible client can call these tools.

**File:** `vcm_os/mcp_server.py`

---

### 9. Async Ingestion Queue (Skeleton)

**Buffered batch processing** for higher throughput:
- `put(event)` — adds to buffer
- `flush()` — processes batch
- Auto-flush timer (5s default)

**Not yet integrated** into production flow (ready for wiring).

**File:** `vcm_os/memory/writer/async_queue.py`

---

### 10. Live Ingestion (Git)

`vcm ingest-git` automatically captures:
- `git diff HEAD` → stored as `code_change`
- `git status --short` → stored as `event`

**File:** `scripts/vcm` (ingest-git subcommand)

---

## Test Results

```
pytest tests/ -x -q
116 passed in 141.63s
```

All existing tests pass. No regressions introduced.

---

## Files Added/Modified

### New Files
```
scripts/vcm
scripts/token_budget_curve.py
scripts/e2e_benchmark_v2.py
scripts/link_quality_eval.py
vcm_os/app/routers/gateway.py
vcm_os/mcp_server.py
vcm_os/memory/writer/async_queue.py
ROADMAP_v1.0.md
ALPHA_COMPLETE_SUMMARY.md
```

### Modified Files
```
vcm_os/schemas/context.py              +max_pack_tokens
vcm_os/context/pack_builder/core.py     dynamic cap/max_items
vcm_os/context/pack_builder/assembler.py request propagation
vcm_os/context/pack_builder/compact_assembler.py request propagation
vcm_os/health/dashboard.py              TTL cache
vcm_os/storage/vector_index.py          lru_cache on encode
vcm_os/app/api.py                       +gateway router
```

---

## Known Limitations

1. **Gateway streaming** — streams responses but cannot verify until full text assembled
2. **MCP server** — not tested with real MCP client yet
3. **Link recall** — heuristic gold standard is imprecise (same_session too broad)
4. **Async queue** — skeleton only, not wired into production flow
5. **E2E weak tasks** — 5 tasks below 0.8, mostly due to truncation of specific keywords
6. **Real session-log restore** — still 0.167, needs live agent data

---

## What to Do Next

### Phase A: Live Agent Integration (Next 2-3 weeks)

These are the highest-impact next steps:

#### A1. Integrate Gateway into Kimi Code CLI
- Modify Kimi Code CLI to route requests through VCM Gateway
- Add `--vcm-project` flag to CLI
- Capture user/assistant exchanges automatically
- **Success metric:** 10 real coding sessions with VCM vs without

#### A2. Capture Tool Outputs Automatically
- Git diff after each assistant response
- Pytest/npm test results
- Docker build output
- **Success metric:** `vcm status` shows events growing during session

#### A3. Real Session Benchmark
- Record 30 real coding sessions (with developer)
- Replay with VCM and without VCM
- Measure: task completion, stale violations, user corrections
- **Success metric:** VCM beats no-VCM on decision correctness and stale suppression

### Phase B: Fix Weak E2E Tasks (1 week)

#### B1. Improve keyword retention
- `auth_rbac`: ensure "Admin", "editor", "viewer" survive truncation
- `error_retries`: ensure "tenacity", "retry", "backoff" in pack
- `debug_race_condition`: ensure "UUID7", "concurrent" in pack

**Approach:** Add protected keyword extraction or increase cap for critical terms.

#### B2. Pack sufficiency v2
- Detect when expected memory types are missing from pack
- Auto-expand with raw evidence fallback
- **Success metric:** all 30 tasks score ≥0.8

### Phase C: Production Hardening (2-3 weeks)

#### C1. Postgres backend
- Implement `PostgresStore` with pgvector
- Migration path from SQLite
- **Success metric:** query p95 <150ms at 100k memories

#### C2. Distributed vector backend
- Qdrant or Milvus integration
- Recall parity with local index
- **Success metric:** ingestion ≥20 mem/s

#### C3. Batch LLM extraction
- Current bottleneck: LLM call per event
- Batch 10 events into single LLM prompt
- **Success metric:** ingestion ≥15 mem/s

#### C4. Streaming gateway verification
- Buffer streaming chunks
- Verify full response when complete
- Return verifier results in final SSE chunk

### Phase D: Product Polish (2-3 weeks)

#### D1. VS Code extension
- Memory panel: active decisions, stale warnings, errors
- "Why is this in context?" hover
- One-click corrections

#### D2. Web dashboard
- Real-time memory health charts
- Project comparison
- Decision timeline visualization

#### D3. Documentation
- API reference (OpenAPI)
- Integration guides (MCP, Gateway, CLI)
- Tutorial: "Add VCM to your agent in 5 minutes"

---

## Success Criteria for v1.0

From ROADMAP_v1.0.md, with current status:

| # | Criterion | Target | Current | Status |
|---|-----------|--------|---------|--------|
| 1 | Live agent integration | Works in CLI/IDE | Gateway works, needs agent hook | 🟡 |
| 2 | Real session-log restore | ≥0.70 | 0.167 | 🔴 |
| 3 | E2E benchmark avg score | ≥0.70 | **0.90** | ✅ |
| 4 | No negative task class | — | 2 negative | 🟡 |
| 5 | Beat RawVerbatim | — | Not tested live | 🔴 |
| 6 | Beat StrongRAG or match | — | Not tested | 🔴 |
| 7 | Dynamic budget curve | Documented | **Done** | ✅ |
| 8 | Human semantic validation | precision ≥0.75 | Not started | 🔴 |
| 9 | Link precision | ≥0.80 | **0.903** | ✅ |
| 10 | Secret redaction | 0 false negatives | **12/12 tests pass** | ✅ |
| 11 | Query p95 | <150ms at 20k | **117ms** | ✅ |
| 12 | Ingestion rate | ≥20 mem/s | 4.3 mem/s | 🔴 |
| 13 | Health snapshot | <500ms at 100k | 1.9s at 20k (with cache) | 🟡 |
| 14 | Production backend | Beyond SQLite | Not started | 🔴 |
| 15 | VS Code/CLI/MCP usable | Non-experts | CLI + Gateway done | 🟡 |

**Already passing:** 3, 7, 9, 10, 11  
**Close:** 1, 4, 13, 15  
**Needs work:** 2, 5, 6, 8, 12, 14

---

## Recommended Immediate Next Action

**Hook VCM Gateway into a real agent workflow.**

The infrastructure is ready. The highest-value validation is:

> Can a developer use VCM for 100 messages of real coding and have a measurably better experience?

This requires:
1. Agent client calling Gateway instead of LLM directly
2. Automatic capture of tool outputs (git, tests)
3. 30 live sessions with A/B comparison

Everything else (Postgres, VS Code, batch extraction) is secondary until this is proven.
