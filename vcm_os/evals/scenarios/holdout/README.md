# VCM-OS Holdout Evaluation Suite

## Rules

1. **Frozen after first run.** Scenarios in this directory cannot be edited after their first evaluation run without explicit holdout review.
2. **Evaluator bugfixes only.** If a scenario fails due to an evaluator bug (wrong expected keyword, malformed event), the fix must be logged in `MUTATION_LOG.md` with justification.
3. **Benchmark mutations require regression.** If scenario text is changed to make it "easier", the old variant must remain as a regression test in `regression/`.
4. **No peeking during optimization.** Do not look at holdout results while tuning pack builder, retrieval, or compression.

## Structure

```
holdout/
  README.md           # this file
  MUTATION_LOG.md     # changelog for any holdout changes
  locked/             # scenarios frozen since creation
  regression/         # old variants kept for regression testing
```

## Current Holdout Scenarios

None yet. v0.6 will populate this directory with 30+ scenarios split from the dev set.

## Acceptance Gates for v0.6

| Metric | Target |
|--------|--------|
| Holdout quality vs Full Context | ≥ parity (Δ ≥ 0) |
| Holdout restore vs Full Context | ≥ parity (Δ ≥ 0) |
| Critical gold survival rate | ≥ 90% |
| Protected term survival rate | ≥ 90% |
| No unexplained duplicate memories | 0 |
| Sparse unique gold hit rate | ≥ 15% on exact-symbol subset |

## How to Add a New Holdout Scenario

1. Move scenario from `dev/` to `holdout/locked/`.
2. Mark `locked=True` in `EvalScenario`.
3. Record in `MUTATION_LOG.md`:
   - scenario_id
   - date_added
   - reason_for_holdout
   - first_run_results
