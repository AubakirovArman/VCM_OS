# VCM-OS VS Code Extension

Validated Context Memory Operating System — memory layer for AI coding agents.

## Features

- **Memory Panel** — Browse decisions, errors, and goals from your project's memory
- **Search** — Find relevant memories across sessions
- **Auto-Ingest** — Automatically capture file saves and git changes
- **Git Ingest** — One-click capture of `git diff` and `git status`
- **Corrections** — Mark memories as stale, incorrect, important, or duplicate

## Requirements

- VCM-OS server running on `localhost:8123`
  ```bash
  vcm serve
  ```

## Setup

1. Install the extension in VS Code
2. Ensure VCM-OS server is running:
   ```bash
   cd /path/to/your/project
   vcm serve
   ```
3. Open a workspace — project ID is auto-detected from folder name

## Commands

| Command | Keybinding | Description |
|---------|-----------|-------------|
| `VCM: Search Memory` | — | Search project memory |
| `VCM: Ingest Git Changes` | — | Capture git diff + status |
| `VCM: Show Project State` | — | Show decisions/errors/goals |
| `VCM: Refresh Memory Panel` | — | Refresh tree view |

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `vcm.apiUrl` | `http://localhost:8123` | VCM API server URL |
| `vcm.projectId` | (auto) | Project identifier |
| `vcm.autoIngest` | `true` | Auto-ingest file saves |
| `vcm.packBudget` | `500` | Default memory pack tokens |

## Kimi Code CLI Integration

Run Kimi with VCM MCP tools:

```bash
kimi term --mcp-config-file /path/to/kimi-vcm-mcp.json --work-dir ./my-project
```

Kimi will automatically use VCM tools to build context and verify responses.
