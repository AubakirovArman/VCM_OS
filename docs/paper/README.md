# VCM-OS Paper Materials

This directory contains all materials needed for the VCM-OS publication.

## Files

| File | Description |
|------|-------------|
| `abstract.md` | Abstract + core contributions |
| `method.md` | Architecture, schema, retrieval pipeline, pack assembly |
| `results_table.md` | LaTeX-ready tables for all results |

## Key Claims

1. **94.2% restore** with **66.1 tokens** (4.7× reduction vs full context)
2. **1.900 quality** — highest across all baselines
3. **Zero stale** on holdout; ablation confirms −0.300 quality drop without stale filter
4. **Zero cross-project contamination** (H03)
5. **Zero false memory rate** (S05)
6. **Exact symbol recall 0.878** with adaptive cap protection

## Data Availability

- Evaluation results: `eval_results_final.json`
- Ablation results: `ablation_results.json`
- Semantic validation: `human_eval_dataset.json`
- Frozen holdout: `vcm_os/evals/scenarios/holdout_scenarios.py`

## Reproducibility

```bash
# Run full evaluation
python -m vcm_os.evals.runner

# Run ablation study
python run_ablations.py

# Run semantic validation
python human_eval_semantic.py
```
