# VCM-OS

Validated Context Memory Operating System for AI and coding agents.

VCM-OS is a local memory runtime for long-running AI development workflows. It stores project events as typed memories, links them into project state, builds compact context packs, and verifies that an agent does not use stale or unsupported memory.

This README is written in three languages:

- [Русский](#русский)
- [English](#english)
- [中文](#中文)

---

## Русский

### Что это

VCM-OS решает проблему длинных AI/coding sessions: агенту не нужно каждый раз тащить всю историю проекта в prompt.

Вместо этого VCM-OS хранит:

- цели проекта;
- активные и отклонённые решения;
- ошибки, failed fixes и verified fixes;
- exact symbols, имена файлов, API routes, config keys;
- tool outputs и test results;
- stale/superseded facts;
- связи между memory objects;
- human corrections.

Обычный RAG делает:

```text
query -> top-k chunks -> prompt
```

VCM-OS делает:

```text
events/tools/code/session
-> typed memories
-> linked project state
-> compact context pack
-> verifier
-> correction/update
```

Идеальный режим использования:

```text
fresh stateless agent
+ current task
+ recent 1-3 turns
+ VCM memory pack
+ files/tools inspected now
```

То есть VCM-OS должен быть long-term memory, а не ещё один большой prompt.

### Текущий статус

Репозиторий уже содержит:

- FastAPI runtime API;
- SQLite event/memory store;
- vector + sparse retrieval;
- context pack builder;
- pack sufficiency / auto-expand logic;
- response verifier;
- secret redaction;
- human correction API;
- MCP server for Kimi and other agent clients;
- CLI scripts;
- eval and regression suites;
- live Kimi MCP smoke test.

Текущая документация по roadmap:

- [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Bilingual LinkedIn Article](docs/LINKEDIN_ARTICLE_BILINGUAL.md)

### Установка

```bash
cd /mnt/hf_model_weights/arman/3bit/VCM_OS

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

Если на машине нет `cuda:3`, запустите embeddings на CPU:

```bash
export VCM_EMBEDDING_DEVICE=cpu
```

Полезные переменные окружения:

```bash
export VCM_DATA_DIR=/path/to/vcm-data
export VCM_EMBEDDING_DEVICE=cpu
export VCM_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
export VLLM_URL=http://127.0.0.1:8000/v1
```

По умолчанию данные лежат в:

```text
data/vcm_os.db
data/vector_index.pkl
data/sparse_index.pkl
```

### Запуск API server

```bash
python3 -m uvicorn vcm_os.app.api:app --host 0.0.0.0 --port 8123
```

Проверка:

```bash
curl -s http://localhost:8123/health
curl -s http://localhost:8123/metrics
```

### Минимальный API workflow

Создать событие:

```bash
curl -s -X POST http://localhost:8123/events \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "event_type": "user_message",
    "raw_text": "Decision: use SQLite for local memory storage."
  }'
```

Построить context pack:

```bash
curl -s -X POST http://localhost:8123/context/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "task_type": "coding",
    "token_budget": 8192,
    "max_pack_tokens": 500
  }'
```

Проверить ответ агента:

```bash
curl -s -X POST http://localhost:8123/verify \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "answer": "The project uses PostgreSQL.",
    "use_llm": false
  }'
```

### Использование с Kimi через MCP

VCM-OS предоставляет MCP server:

```text
scripts/vcm-mcp-stdio
scripts/vcm-mcp-http
```

В репозитории уже есть config:

```text
kimi-vcm-mcp.json
```

Он подключает stdio MCP server:

```json
{
  "mcpServers": {
    "vcm": {
      "command": "python3",
      "args": ["./scripts/vcm-mcp-stdio"],
      "env": {}
    }
  }
}
```

Если вы запускаете из другого каталога, используйте абсолютный путь к `scripts/vcm-mcp-stdio`.

Проверить MCP server в Kimi:

```bash
kimi mcp test vcm
```

Если server ещё не добавлен глобально:

```bash
kimi mcp add --transport stdio vcm -- \
  python3 /mnt/hf_model_weights/arman/3bit/VCM_OS/scripts/vcm-mcp-stdio

kimi mcp test vcm
```

Запуск Kimi с VCM tools:

```bash
kimi --print --final-message-only --yolo \
  --mcp-config-file /mnt/hf_model_weights/arman/3bit/VCM_OS/kimi-vcm-mcp.json \
  --work-dir /path/to/your/project \
  -p 'Use VCM MCP tools. First call vcm_build_context for project_id="my_project". Then complete the task and call vcm_write_event with changed files, decisions, and checks.'
```

Доступные MCP tools:

```text
vcm_build_context
vcm_write_event
vcm_verify_response
vcm_search_memory
vcm_correct_memory
vcm_get_project_state
```

### Stateful Kimi vs stateless Kimi

Для обычной разработки можно использовать Kimi session resume:

```bash
kimi -r <session_id>
kimi --continue
```

Но для проверки экономии токенов так делать нельзя: Kimi будет тащить свою chat history, и VCM не будет единственным источником долгой памяти.

Для честного VCM теста используйте stateless режим:

```text
1. Каждый turn запускает новый Kimi process.
2. Не используйте -r, --session, --continue.
3. Используйте постоянный VCM project_id/session_id.
4. В начале turn вызывайте vcm_build_context.
5. В конце turn вызывайте vcm_write_event.
```

Пример stateless prompt:

```text
You are a fresh stateless coding agent.
Do not assume prior chat history.
Use only:
1. the current request,
2. VCM memory returned by vcm_build_context,
3. files/tools you inspect now.

First call:
vcm_build_context(project_id="my_project", session_id="sess_live", query="...", task_type="coding", max_pack_tokens=700)

After the work, call:
vcm_write_event(project_id="my_project", session_id="sess_live", event_type="assistant_response", raw_text="Turn complete: changed files; decisions; checks; TODOs")
```

Такой режим позволяет сравнить:

```text
fresh agent without VCM
fresh agent + VCM
full-history agent
RawVerbatim / StrongRAG
```

### CLI scripts

Запуск VCM API:

```bash
scripts/vcm serve --port 8123
```

Запуск Kimi с MCP config:

```bash
scripts/vcm-kimi term --work-dir /path/to/project
```

Запуск команды с capture в VCM:

```bash
scripts/vcm run --project my_project --session sess_tests pytest -q
```

Поиск по памяти:

```bash
scripts/vcm memory search "cache migration decision" --project my_project
```

Ингест git diff:

```bash
scripts/vcm ingest-git --project my_project --session sess_git
```

### Тесты и проверки

```bash
pytest -q
python3 -m compileall -q vcm_os tests
python3 scripts/token_budget_curve.py
python3 scripts/e2e_benchmark.py
python3 scripts/load_test.py
```

На последней локальной проверке основной набор проходил:

```text
118 passed
```

### Основные endpoints

```text
POST /events
POST /memory/write
POST /memory/read
GET  /memory/{memory_id}
POST /memory/correct
GET  /memory/review-queue/{project_id}

POST /context/build
POST /context/prompt
POST /verify

POST /session/create
POST /session/{session_id}/restore
POST /session/save

GET  /project/{project_id}/state
GET  /project/{project_id}/decisions
GET  /project/{project_id}/errors

POST /codebase/index
POST /codebase/symbols/search

POST /gateway/chat/completions

GET  /health
GET  /metrics
GET  /dashboard/health
```

### Когда VCM реально экономит токены

VCM экономит токены только если агент не тащит всю старую историю параллельно.

Плохой тест:

```text
Kimi resume session + VCM
```

Хороший тест:

```text
fresh Kimi process + current task + VCM context pack
```

Тогда full-history растёт с каждым turn, а VCM pack остаётся ограниченным бюджетом:

```text
simple continuation: 100-300 tokens
normal coding:       300-700 tokens
debugging:           700-1500 tokens
architecture:        1500-5000 tokens
```

---

## English

### What It Is

VCM-OS is a local memory runtime for AI and coding agents. It is designed for long-running development workflows where repeatedly sending the full conversation history is expensive, noisy, and unreliable.

VCM-OS stores:

- project goals;
- active and rejected decisions;
- errors, failed fixes, and verified fixes;
- exact symbols, file names, API routes, config keys;
- tool outputs and test results;
- stale or superseded facts;
- links between memory objects;
- human corrections.

Classic RAG:

```text
query -> top-k chunks -> prompt
```

VCM-OS:

```text
events/tools/code/session
-> typed memories
-> linked project state
-> compact context pack
-> verifier
-> correction/update
```

The target workflow is:

```text
fresh stateless agent
+ current task
+ recent 1-3 turns
+ VCM memory pack
+ files/tools inspected now
```

VCM-OS should be long-term memory, not another huge prompt.

### Current Status

The repository includes:

- FastAPI runtime API;
- SQLite event and memory store;
- vector + sparse retrieval;
- context pack builder;
- pack sufficiency / auto-expand logic;
- response verifier;
- secret redaction;
- human correction API;
- MCP server for Kimi and other agent clients;
- CLI scripts;
- eval and regression suites;
- live Kimi MCP smoke test.

Useful docs:

- [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Bilingual LinkedIn Article](docs/LINKEDIN_ARTICLE_BILINGUAL.md)

### Installation

```bash
cd /mnt/hf_model_weights/arman/3bit/VCM_OS

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

If your machine does not have `cuda:3`, run embeddings on CPU:

```bash
export VCM_EMBEDDING_DEVICE=cpu
```

Common environment variables:

```bash
export VCM_DATA_DIR=/path/to/vcm-data
export VCM_EMBEDDING_DEVICE=cpu
export VCM_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
export VLLM_URL=http://127.0.0.1:8000/v1
```

Default data files:

```text
data/vcm_os.db
data/vector_index.pkl
data/sparse_index.pkl
```

### Start the API Server

```bash
python3 -m uvicorn vcm_os.app.api:app --host 0.0.0.0 --port 8123
```

Check it:

```bash
curl -s http://localhost:8123/health
curl -s http://localhost:8123/metrics
```

### Minimal API Workflow

Write an event:

```bash
curl -s -X POST http://localhost:8123/events \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "event_type": "user_message",
    "raw_text": "Decision: use SQLite for local memory storage."
  }'
```

Build a context pack:

```bash
curl -s -X POST http://localhost:8123/context/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "task_type": "coding",
    "token_budget": 8192,
    "max_pack_tokens": 500
  }'
```

Verify an agent answer:

```bash
curl -s -X POST http://localhost:8123/verify \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "answer": "The project uses PostgreSQL.",
    "use_llm": false
  }'
```

### Use with Kimi via MCP

VCM-OS provides MCP servers:

```text
scripts/vcm-mcp-stdio
scripts/vcm-mcp-http
```

The repo includes:

```text
kimi-vcm-mcp.json
```

It connects the stdio MCP server:

```json
{
  "mcpServers": {
    "vcm": {
      "command": "python3",
      "args": ["./scripts/vcm-mcp-stdio"],
      "env": {}
    }
  }
}
```

If you run Kimi from another directory, use an absolute path to `scripts/vcm-mcp-stdio`.

Test the MCP server:

```bash
kimi mcp test vcm
```

If it is not registered globally:

```bash
kimi mcp add --transport stdio vcm -- \
  python3 /mnt/hf_model_weights/arman/3bit/VCM_OS/scripts/vcm-mcp-stdio

kimi mcp test vcm
```

Run Kimi with VCM tools:

```bash
kimi --print --final-message-only --yolo \
  --mcp-config-file /mnt/hf_model_weights/arman/3bit/VCM_OS/kimi-vcm-mcp.json \
  --work-dir /path/to/your/project \
  -p 'Use VCM MCP tools. First call vcm_build_context for project_id="my_project". Then complete the task and call vcm_write_event with changed files, decisions, and checks.'
```

Available MCP tools:

```text
vcm_build_context
vcm_write_event
vcm_verify_response
vcm_search_memory
vcm_correct_memory
vcm_get_project_state
```

### Stateful Kimi vs Stateless Kimi

For normal interactive development, Kimi resume is useful:

```bash
kimi -r <session_id>
kimi --continue
```

But this does not prove token savings. Kimi will still carry its own chat history.

For a fair VCM token-economy test:

```text
1. Start a fresh Kimi process for every turn.
2. Do not use -r, --session, or --continue.
3. Keep VCM project_id/session_id persistent.
4. Call vcm_build_context at the start.
5. Call vcm_write_event at the end.
```

Prompt pattern:

```text
You are a fresh stateless coding agent.
Do not assume prior chat history.
Use only:
1. the current request,
2. VCM memory returned by vcm_build_context,
3. files/tools you inspect now.

First call:
vcm_build_context(project_id="my_project", session_id="sess_live", query="...", task_type="coding", max_pack_tokens=700)

After the work, call:
vcm_write_event(project_id="my_project", session_id="sess_live", event_type="assistant_response", raw_text="Turn complete: changed files; decisions; checks; TODOs")
```

This lets you compare:

```text
fresh agent without VCM
fresh agent + VCM
full-history agent
RawVerbatim / StrongRAG
```

### CLI Scripts

Start VCM API:

```bash
scripts/vcm serve --port 8123
```

Start Kimi with MCP config:

```bash
scripts/vcm-kimi term --work-dir /path/to/project
```

Capture command output into VCM:

```bash
scripts/vcm run --project my_project --session sess_tests pytest -q
```

Search memory:

```bash
scripts/vcm memory search "cache migration decision" --project my_project
```

Ingest git diff:

```bash
scripts/vcm ingest-git --project my_project --session sess_git
```

### Tests

```bash
pytest -q
python3 -m compileall -q vcm_os tests
python3 scripts/token_budget_curve.py
python3 scripts/e2e_benchmark.py
python3 scripts/load_test.py
```

Latest local full test result:

```text
118 passed
```

### Key Endpoints

```text
POST /events
POST /memory/write
POST /memory/read
GET  /memory/{memory_id}
POST /memory/correct
GET  /memory/review-queue/{project_id}

POST /context/build
POST /context/prompt
POST /verify

POST /session/create
POST /session/{session_id}/restore
POST /session/save

GET  /project/{project_id}/state
GET  /project/{project_id}/decisions
GET  /project/{project_id}/errors

POST /codebase/index
POST /codebase/symbols/search

POST /gateway/chat/completions

GET  /health
GET  /metrics
GET  /dashboard/health
```

### When VCM Actually Saves Tokens

VCM saves tokens only when the agent does not carry the full old chat history in parallel.

Bad test:

```text
Kimi resume session + VCM
```

Good test:

```text
fresh Kimi process + current task + VCM context pack
```

Suggested pack budgets:

```text
simple continuation: 100-300 tokens
normal coding:       300-700 tokens
debugging:           700-1500 tokens
architecture:        1500-5000 tokens
```

---

## 中文

### 这是什么

VCM-OS 是一个面向 AI agent 和 coding agent 的本地记忆运行时。它的目标是解决长时间开发会话中的一个核心问题：agent 不应该在每次请求中都携带完整历史对话。

VCM-OS 会存储：

- 项目目标；
- 当前有效的决策和已拒绝的决策；
- 错误、失败的修复、已验证的修复；
- 精确符号、文件名、API route、配置 key；
- 工具输出和测试结果；
- 过期或被替代的事实；
- memory objects 之间的链接；
- 人工修正。

传统 RAG 通常是：

```text
query -> top-k chunks -> prompt
```

VCM-OS 的流程是：

```text
events/tools/code/session
-> typed memories
-> linked project state
-> compact context pack
-> verifier
-> correction/update
```

理想的使用方式：

```text
fresh stateless agent
+ current task
+ recent 1-3 turns
+ VCM memory pack
+ files/tools inspected now
```

也就是说，VCM-OS 应该成为长期项目记忆，而不是另一个巨大的 prompt。

### 当前状态

仓库目前包含：

- FastAPI runtime API；
- SQLite event/memory store；
- vector + sparse retrieval；
- context pack builder；
- pack sufficiency / auto-expand 逻辑；
- response verifier；
- secret redaction；
- human correction API；
- 面向 Kimi 和其他 agent client 的 MCP server；
- CLI scripts；
- eval 和 regression suites；
- live Kimi MCP smoke test。

相关文档：

- [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Bilingual LinkedIn Article](docs/LINKEDIN_ARTICLE_BILINGUAL.md)

### 安装

```bash
cd /mnt/hf_model_weights/arman/3bit/VCM_OS

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

如果机器没有 `cuda:3`，请使用 CPU embeddings：

```bash
export VCM_EMBEDDING_DEVICE=cpu
```

常用环境变量：

```bash
export VCM_DATA_DIR=/path/to/vcm-data
export VCM_EMBEDDING_DEVICE=cpu
export VCM_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
export VLLM_URL=http://127.0.0.1:8000/v1
```

默认数据文件：

```text
data/vcm_os.db
data/vector_index.pkl
data/sparse_index.pkl
```

### 启动 API Server

```bash
python3 -m uvicorn vcm_os.app.api:app --host 0.0.0.0 --port 8123
```

检查服务：

```bash
curl -s http://localhost:8123/health
curl -s http://localhost:8123/metrics
```

### 最小 API 流程

写入事件：

```bash
curl -s -X POST http://localhost:8123/events \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "event_type": "user_message",
    "raw_text": "Decision: use SQLite for local memory storage."
  }'
```

构建 context pack：

```bash
curl -s -X POST http://localhost:8123/context/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "task_type": "coding",
    "token_budget": 8192,
    "max_pack_tokens": 500
  }'
```

验证 agent 回答：

```bash
curl -s -X POST http://localhost:8123/verify \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "session_id": "sess_demo",
    "query": "What storage decision was made?",
    "answer": "The project uses PostgreSQL.",
    "use_llm": false
  }'
```

### 通过 MCP 与 Kimi 使用

VCM-OS 提供 MCP server：

```text
scripts/vcm-mcp-stdio
scripts/vcm-mcp-http
```

仓库中已有配置文件：

```text
kimi-vcm-mcp.json
```

它连接 stdio MCP server：

```json
{
  "mcpServers": {
    "vcm": {
      "command": "python3",
      "args": ["./scripts/vcm-mcp-stdio"],
      "env": {}
    }
  }
}
```

如果你从其他目录运行 Kimi，请使用 `scripts/vcm-mcp-stdio` 的绝对路径。

测试 MCP server：

```bash
kimi mcp test vcm
```

如果还没有全局注册：

```bash
kimi mcp add --transport stdio vcm -- \
  python3 /mnt/hf_model_weights/arman/3bit/VCM_OS/scripts/vcm-mcp-stdio

kimi mcp test vcm
```

使用 VCM tools 启动 Kimi：

```bash
kimi --print --final-message-only --yolo \
  --mcp-config-file /mnt/hf_model_weights/arman/3bit/VCM_OS/kimi-vcm-mcp.json \
  --work-dir /path/to/your/project \
  -p 'Use VCM MCP tools. First call vcm_build_context for project_id="my_project". Then complete the task and call vcm_write_event with changed files, decisions, and checks.'
```

可用 MCP tools：

```text
vcm_build_context
vcm_write_event
vcm_verify_response
vcm_search_memory
vcm_correct_memory
vcm_get_project_state
```

### Stateful Kimi 与 Stateless Kimi

普通交互式开发可以使用 Kimi resume：

```bash
kimi -r <session_id>
kimi --continue
```

但这不能证明 VCM 节省 token，因为 Kimi 仍然会携带自己的对话历史。

如果要公平测试 VCM 的 token economy：

```text
1. 每个 turn 都启动新的 Kimi process。
2. 不使用 -r、--session、--continue。
3. 保持 VCM project_id/session_id 不变。
4. 每个 turn 开始时调用 vcm_build_context。
5. 每个 turn 结束时调用 vcm_write_event。
```

Prompt 模板：

```text
You are a fresh stateless coding agent.
Do not assume prior chat history.
Use only:
1. the current request,
2. VCM memory returned by vcm_build_context,
3. files/tools you inspect now.

First call:
vcm_build_context(project_id="my_project", session_id="sess_live", query="...", task_type="coding", max_pack_tokens=700)

After the work, call:
vcm_write_event(project_id="my_project", session_id="sess_live", event_type="assistant_response", raw_text="Turn complete: changed files; decisions; checks; TODOs")
```

这样可以比较：

```text
fresh agent without VCM
fresh agent + VCM
full-history agent
RawVerbatim / StrongRAG
```

### CLI Scripts

启动 VCM API：

```bash
scripts/vcm serve --port 8123
```

使用 MCP config 启动 Kimi：

```bash
scripts/vcm-kimi term --work-dir /path/to/project
```

把命令输出写入 VCM：

```bash
scripts/vcm run --project my_project --session sess_tests pytest -q
```

搜索记忆：

```bash
scripts/vcm memory search "cache migration decision" --project my_project
```

导入 git diff：

```bash
scripts/vcm ingest-git --project my_project --session sess_git
```

### 测试

```bash
pytest -q
python3 -m compileall -q vcm_os tests
python3 scripts/token_budget_curve.py
python3 scripts/e2e_benchmark.py
python3 scripts/load_test.py
```

最近一次本地完整测试结果：

```text
118 passed
```

### 主要 Endpoints

```text
POST /events
POST /memory/write
POST /memory/read
GET  /memory/{memory_id}
POST /memory/correct
GET  /memory/review-queue/{project_id}

POST /context/build
POST /context/prompt
POST /verify

POST /session/create
POST /session/{session_id}/restore
POST /session/save

GET  /project/{project_id}/state
GET  /project/{project_id}/decisions
GET  /project/{project_id}/errors

POST /codebase/index
POST /codebase/symbols/search

POST /gateway/chat/completions

GET  /health
GET  /metrics
GET  /dashboard/health
```

### VCM 什么时候真正节省 token

只有当 agent 不同时携带完整旧对话历史时，VCM 才能真正节省 token。

不好的测试：

```text
Kimi resume session + VCM
```

好的测试：

```text
fresh Kimi process + current task + VCM context pack
```

建议的 pack budgets：

```text
simple continuation: 100-300 tokens
normal coding:       300-700 tokens
debugging:           700-1500 tokens
architecture:        1500-5000 tokens
```
