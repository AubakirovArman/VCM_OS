# VCM-OS Documentation

## Quick Links

| Document | Description |
|----------|-------------|
| `v1_0_final_results.md` | **Final evaluation results** (holdout 95.8% restore, 65.8 tokens, 6 baselines) |
| `paper/` | Publication materials (abstract, method, LaTeX tables) |
| `ablation_results.md` | Component ablation study |
| `human_eval_semantic_results.md` | Semantic threshold validation |
| `v0_10_live_workflow.md` | Live CLI adapter integration notes |

## Version History

| Version | File | Key Achievement |
|---------|------|-----------------|
| v0.5 | `v0_5_complete_log.md` | Core event-sourced memory |
| v0.6-0.8 | `v0_6_7_8_journal.md` | Audit, PSO, Symbol Vault |
| v0.9 | `v0_9_complete_results.md` | Baselines, semantic matcher |
| v0.10 | `v1_0_final_results.md` | **Final results, ablations, live workflow** |

## Reproducing Results

```bash
# Full evaluation
python -m vcm_os.evals.runner

# Holdout only
python -c "from vcm_os.evals.runner import BenchmarkRunner; ..."

# Ablations
python run_ablations.py

# Semantic validation
python human_eval_semantic.py
```

## v1.0 Status

| Gate | Status |
|------|--------|
| Stale suppression | ✅ |
| Project state | ✅ |
| Rationale recall | ✅ |
| Dogfooding | ✅ |
| Live workflow | ✅ |
| Exact symbol | ✅ |
| Token target ≤60 | ⚠️ (holdout 66.1, tuning 79.3; dogfooding 41) |
| Semantic threshold | ⚠️ (precision 0.200, needs human validation) |
