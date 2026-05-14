# VCM-OS v0.10 Live Workflow Integration

> **Date:** 2026-05-10  
> **Status:** CLI adapter working with real LLM (Gemma 4 31B)

---

## CLI Adapter

File: `vcm_cli_adapter.py`

### What it does
1. Initializes VCM-OS (SQLite, vector, sparse indexes)
2. Creates/loads project session
3. Accepts user input
4. Records user message as VCM event
5. Builds context pack from project memory
6. Sends pack + query to LLM (localhost:8000)
7. Records LLM response as VCM event
8. Updates Project State Object
9. Shows response to user

### Demo

```bash
export VCM_LLM_API_KEY="<your-api-key>"
export VCM_LLM_URL="http://localhost:8000/v1/chat/completions"
python test_cli_adapter.py
```

### Result

**Query:** "What decisions have we made about auth?"

**Context Pack (proj_auth):**
```
g=Requirement: We need to fix the auth refresh token loop. ...
t=Assistant plan: I'll investigate validateSession in src/a...
d=Decision: use httpOnly cookie for refresh token. Middlewa...
b=Error (test_failure): tests/auth.test.ts still failing: r...
f=src/auth/session.ts

p=proj_auth q=What decisions have
f=src/auth/session.ts,src/auth/middleware.ts
use httpOnly cookie for refresh token. Rationale: reduces XSS exposure.
Middleware must not refresh on every request. Rationale: avoid recursive refresh calls.
pytest auth suite: 12 passed, 0 failed.
Files: src/auth/session.ts. Terms: Modified, refreshSession,
```

**Pack size:** 680 chars / ~170 tokens

**LLM Response:**
> Based on the project context provided, the following decisions have been made regarding authentication:
> - **Refresh Token Storage:** The refresh token will be stored in an **`httpOnly` cookie**.
> - **Rationale:** This decision was made to reduce exposure to Cross-Site Scripting (XSS) attacks.
> - **Middleware Logic:** It was decided that the middleware must not refresh the session recursively.

---

## Verification

✅ VCM-OS correctly retrieved decisions from memory  
✅ LLM answered based on VCM context pack  
✅ Rationales included in pack  
✅ Token count reasonable (~170 tokens for full project state)  

---

## Files

| File | Purpose |
|------|---------|
| `vcm_cli_adapter.py` | Interactive REPL with VCM memory |
| `test_cli_adapter.py` | Single-turn demo script |

---

## Usage

```bash
# Start interactive session
python vcm_cli_adapter.py --project my_project

# Commands:
#   Type any question → LLM answers with VCM context
#   pack → show current context pack
#   exit → save and quit
```
