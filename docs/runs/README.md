# VCM-OS Eval Runs — Append-Only Log

## Rule

**NEVER edit existing run files. Only append new ones.**

Each time you run eval, create a NEW file. If something was wrong in a previous run, leave it as-is and document the fix in the NEXT file.

## Naming Convention

```
v{version}_{run_id}_YYYYMMDD_HHMMSS.md
```

Examples:
```
v0.5_run_v1_20260510_143022.md
v0.5_run_v2_20260510_150145.md
v0.5_run_v3_20260510_153012.md
v0.5_run_v5.5_20260510_215507.md
v0.6_run_v1_20260511_090000.md
```

## File Template

```markdown
# Run ID: v0.5_run_v5.5
# Date: 2026-05-10 21:55:07
# What changed from previous run:
# - Added rare-term rescue pass
# - Fixed SHA256 canonicalization
# - Added regression scenario

## Metrics

| Metric | VCM | Full | Delta |
|--------|-----|------|-------|
| Quality | ... | ... | ... |
| Restore | ... | ... | ... |
| Tokens | ... | ... | ... |

## Per-Scenario

| Scenario | VCM | Full | Delta |
|----------|-----|------|-------|

## What worked

## What failed

## What was fixed

## What is still broken

## Next hypothesis
```

## Archive

| Run | Date | Key Change | Quality | Restore | Tokens |
|-----|------|-----------|---------|---------|--------|
