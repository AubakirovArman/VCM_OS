# VCM-OS v0.5 — Virtual Context Memory Operating System

Реализация v0.1–v0.5 исследовательского blueprint для системы виртуализации контекста памяти LLM-агентов.

## Архитектура

```
Conversation/Tool Events
        ↓
Append-only Event Log (SQLite)
        ↓
Memory Writer (rule-based + LLM extraction)
        ↓
Typed Memory Objects
        ↓
SQLite metadata + Vector Index + BM25 Sparse Index + Graph Links
        ↓
Decision Ledger + Error Ledger + Reflection Engine
        ↓
Codebase Index (AST) + Symbol Graph + Stale Checker
        ↓
Session Checkpoint
        ↓
Memory Router (task-aware) + Query Rewriter + Reranker (RRF)
        ↓
Context Pack Builder (adaptive budget + sufficiency checker)
        ↓
Verifier (consistency check)
        ↓
Prompt Composer
        ↓
LLM
```

## Стек

- **Storage:** SQLite (метаданные, сессии, ledgers, граф ссылок)
- **Vector Search:** sentence-transformers + numpy cosine similarity (GPU 3)
- **Sparse Search:** rank_bm25 (BM25Okapi)
- **Embeddings:** BAAI/bge-small-en-v1.5 на `cuda:3`
- **LLM API:** vLLM endpoint (Gemma 4 31B) для extraction, query rewriting, sufficiency check, reflection, summaries
- **AST Parsing:** Python `ast` модуль для codebase index
- **API:** FastAPI (порт 8123)
- **Eval:** pytest + 23 synthetic scenarios + benchmark suite

## Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка LLM API (опционально)
export VCM_LLM_URL="http://localhost:8000/v1"
export VCM_LLM_API_KEY="your_key"
export VCM_LLM_MODEL="google/gemma-4-31B-it"

# Запуск сервера
python main.py
# или
uvicorn vcm_os.app.api:app --host 0.0.0.0 --port 8123

# Проверка всей системы
python verify_system.py

# Тесты
pytest tests/ -v

# Eval benchmark suite
PYTHONPATH=$(pwd) python3 vcm_os/evals/runner.py
```

## Компоненты

### v0.1 Core
- **Schemas** — Pydantic модели для всех объектов
- **SQLite Store** — events, memories, sessions, checkpoints, links
- **Vector / Sparse Index** — dense + BM25 retrieval
- **Memory Writer** — извлечение typed memory objects
- **Memory Reader / Router / Scorer** — hybrid retrieval
- **Context Pack Builder** — сборка контекста под token budget
- **Session Store / Checkpoint / Restore** — управление сессиями
- **Decision / Error Ledgers** — CRUD для решений и ошибок

### v0.2 Advanced Retrieval
- **LLM Client** — асинхронный клиент для vLLM API
- **Query Rewriter** — LLM-based query expansion
- **Reranker + RRF** — Reciprocal Rank Fusion
- **Graph Expander** — multi-hop через memory links
- **Reflection Engine** — evidence-based reflection
- **Decay Engine** — typed decay с half-life
- **Stale Checker** — проверка устаревших references
- **Sufficiency Checker** — оценка достаточности pack

### v0.3 Codebase & Verification
- **AST Indexer** — парсинг Python кода, извлечение функций/классов/импортов
- **Symbol Graph** — call graph, affected symbols, dependency chains
- **Consistency Verifier** — проверка contradiction, contamination, citations
- **Summary Generator** — LLM-powered session/project/file summaries

### v0.5 Eval Harness (Gold Scenarios)
- **23 Synthetic Scenarios** — multi-session coding projects с decisions, errors, stale facts, project switching
- **Baselines** — Summary (compressed), RAG (vector-only), Full Context (all memories)
- **Experiments:**
  - **T10** — VCM vs baselines (restore accuracy, token usage, keyword coverage, stale penalty)
  - **H03** — Cross-session contamination (3 projects с conflicting decisions)
  - **S05** — False memory insertion (detection & rejection)
  - **F03** — Hybrid retrieval benchmark (dense vs hybrid)
  - **I01** — Project state restore accuracy
- **Report Generator** — автоматический отчёт с pass/fail по threshold

## API Endpoints

### v0.1–v0.3 Endpoints
`POST /events`, `POST /memory/read`, `POST /context/build`, `POST /context/prompt`, `POST /session/create`, `POST /session/{id}/restore`, `POST /session/save`, `GET /project/{id}/decisions`, `GET /project/{id}/errors`, `GET /memory/{id}`, `POST /memory/graph/expand`, `POST /memory/reflect`, `POST /memory/decay`, `POST /memory/stale`, `POST /query/rewrite`, `POST /codebase/index`, `POST /verify`, `POST /summaries/session`, `POST /summaries/project`, `GET /health`

## GPU

Embedding модель загружается на GPU с id=3 (`cuda:3`). Настраивается через `VCM_EMBEDDING_DEVICE`.

## Проверка системы

### 1. Полная системная проверка
```bash
python verify_system.py
```

Проверяет:
- 17 unit tests (v0.1 core + v0.2 retrieval + v0.3 AST/verifier)
- 5 eval tests (T10, H03, S05, baselines, hybrid)
- API smoke tests: sessions, events, memory retrieval, context pack, ledgers, decay, stale check, graph expansion, query rewrite, session restore, verifier, codebase index, symbol search

### 2. Eval Benchmark Suite
```bash
PYTHONPATH=$(pwd) python3 vcm_os/evals/runner.py
```

Запускает 23 synthetic scenarios через 5 экспериментов:
- **T10** — сравнение VCM vs Summary vs RAG vs Full Context
- **H03** — cross-project contamination
- **S05** — false memory detection
- **F03** — hybrid retrieval improvement
- **I01** — project state restore accuracy

Результаты сохраняются в `eval_results.json` и `eval_report.txt`.

### 3. Пример eval-отчёта

```
## T10: VCM vs Baselines
  VCM:
    Restore accuracy:    0.769
    Token usage (avg):   418
    Keyword coverage:    0.939
    Stale penalty:       0.105
    Quality score:       1.602
  SUMMARY:
    Restore accuracy:    0.713
    Token usage (avg):   133
    Quality score:       1.529
  RAG:
    Restore accuracy:    0.643
    Token usage (avg):   361
    Quality score:       1.363
  VCM beats summary: YES
  VCM beats RAG: YES

## H03: Cross-Session Contamination
  Contamination rate: 0.0000
  Passes threshold (<0.02): YES

## S05: False Memory Insertion
  False memory rate: 0.000
  Passes threshold (<0.05): YES

## I01: Project State Restore
  Avg restore accuracy: 0.689
  Passes threshold (0.80): NO
```

### 4. Ручное тестирование endpoints

```bash
# Health
curl -s http://localhost:8123/health

# Create session
curl -s -X POST http://localhost:8123/session/create \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo","title":"Test"}'

# Write event
curl -s -X POST http://localhost:8123/events \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo","event_type":"user_message","raw_text":"Decision: use Redis."}'

# Build context
curl -s -X POST http://localhost:8123/context/build \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo","query":"What DB?","token_budget":4000}'

# Verify answer
curl -s -X POST http://localhost:8123/verify \
  -H "Content-Type: application/json" \
  -d '{"query":"What DB?","answer":"We use MySQL.","project_id":"demo","use_llm":false}'

# Index codebase
curl -s -X POST http://localhost:8123/codebase/index \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo","directory":"./vcm_os"}'

# Search symbol
curl -s -X POST http://localhost:8123/codebase/symbols/search \
  -H "Content-Type: application/json" \
  -d '{"name":"MemoryWriter"}'
```

## Что реализовано из plan.md

### v0.1 ✅
Event log, Typed Memory Objects, Session management, Decision/Error Ledgers, Hybrid Retrieval, Context Pack Builder, Session Restore, Evaluation Harness, Contradiction detection, Memory linking

### v0.2 ✅
LLM-powered Extraction, RRF Fusion, Query Rewriting, Reranker, Graph Expansion, Pack Sufficiency Checker, Reflection Engine, Decay Engine, Stale Detection, Adaptive Compression

### v0.3 ✅
AST-based Codebase Index, Symbol Graph (call graph, affected symbols, dependency chains), Consistency Verifier, LLM-powered Summary Generator

### v0.5 ✅
23 Gold Eval Scenarios, Baselines (Summary/RAG/Full), T10/H03/S05/F03/I01 Experiments, Benchmark Runner, Automated Report Generation

### Отложено на v1.0+
Graph DB (Neo4j/Kuzu), Multi-user/tenant, RBAC, Audit/Debug UI, Monitoring dashboards, Learned memory controller, Multi-agent memory manager, Procedural auto-evolution
