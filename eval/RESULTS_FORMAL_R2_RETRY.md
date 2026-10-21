# Formal Formative — r2_retry

Updated: 2026-10-21T15:31:49+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_formal_r2_retry_20261021-153116`
Provider/Model: **bailian / qwen3.8-max** · seeds=**[1]** · check max_rounds=**3**

## Aggregate success (semantic / ConstraintChecker)

- **constraint**: baseline n/a · check 2/2 (100%)
- **all**: baseline n/a · check 2/2 (100%)

## Per-seed

- seed=1: baseline n/a · check 2/2 (100%)

## Matrix

| seed | prompt | condition | harness_ok | semantic/check_ok | rounds | notes |
|---|---|---|---|---|---|---|
| 1 | P05_constraint_on_top | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=3 failed=0 skipped=0 set=P05_on_top", "failed` |
| 1 | P08_constraint_no_overlap | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "fa` |

CSV: `results_formal_r2_retry_20261021-153149.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_r2_retry_20261021-153116/manifest.ndjson`

