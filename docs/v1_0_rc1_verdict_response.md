# Response to v1.0 RC1 Verdict

**Date:** 2026-05-10  
**Status:** RC1 confirmed, final v1.0 blocked on 3 items  
**Action:** Create hardening plan, execute in priority order

---

## Verdict Summary

| Item | Verdict | Action Required |
|------|---------|-----------------|
| RC1 | **GO** | Tag as `v1.0-rc1` |
| Final v1.0 | **NO-GO** | Fix 3 blockers first |

---

## Blockers (Priority Order)

### Blocker 1: Semantic Precision 0.200
**Problem:** Semantic matcher at 0.75 has precision 0.200 — too low for headline metric.  
**Fix Options:**
- Option A: Human-label 100-200 pairs, calibrate threshold for precision ≥0.75
- Option B: Remove semantic restore from headline, keep as diagnostic only

**Decision:** Start Option A (human labeling pipeline). If precision cannot reach 0.75, fall back to Option B.

### Blocker 2: Exact CI/CD Job 0.667
**Problem:** Long exact identifiers truncated despite adaptive cap.  
**Fix:** Separate `exact_symbol` field (never truncated) from `display_context` (truncated).  
**Target:** Exact-symbol recall ≥0.90, no class below 0.80.

### Blocker 3: Report Consistency
**Problems:**
- Tuning baseline table uses holdout Full Context numbers (copy/paste)
- Missing RawVerbatim/StrongRAG in main holdout table
- No clean split manifest (holdout_20 IDs, tuning_29 IDs)

**Fix:**
- Generate separate baseline runs per split
- Add RawVerbatim + StrongRAG to holdout table
- Create `split_manifest.yaml` with scenario IDs, hashes, freeze dates

---

## Additional Improvements (Post-RC1)

| # | Item | Target | Effort |
|---|------|--------|--------|
| 4 | Separate restore metrics | `restore_verbatim`, `restore_exact`, `restore_semantic` | Low |
| 5 | I01 state restore ≥0.80 | Improve PSO extraction or narrow claims | Medium |
| 6 | Real codebase expansion | 3→10+ scenarios | High |
| 7 | Stale-aware Full Context baseline | Fair comparison | Low |

---

## Revised Release Statement

```text
VCM-OS v1.0 RC1 achieves strong results on a 20-scenario frozen holdout:
restore 0.958 with 63.4 average tokens, compared with Full Context restore
0.920 at 310.7 tokens. This is a 4.9× token reduction and ~79.6% dynamic
reduction. VCM achieves zero stale facts and the highest memory-management
composite quality on the holdout. Stale-filter ablation shows the largest
component impact (−0.300 quality).

v1.0 remains a release candidate: semantic precision is 0.200, exact-symbol
recall is 0.878 with CI/CD job truncation at 0.667, I01 state restore is 0.667,
and RawVerbatim/StrongRAG baselines are not yet in the headline table.
```

---

## Next Actions (This Session)

1. [ ] Create `split_manifest.yaml` with holdout_20 + tuning_29 IDs
2. [ ] Add RawVerbatim + StrongRAG to holdout baseline table
3. [ ] Separate restore metrics (verbatim/exact/semantic)
4. [ ] Fix exact-symbol truncation for long CI/CD names
5. [ ] Start human semantic validation pipeline
