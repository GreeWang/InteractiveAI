# Formal Formative — multiseed_qwen

Updated: 2026-10-21T15:50:25+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_formal_multiseed_qwen_20261021-154240`
Provider/Model: **bailian / qwen3.8-max** · seeds=**[2, 3]** · check max_rounds=**3**

## Aggregate success (semantic / ConstraintChecker)

- **edit**: baseline 6/6 (100%) · check 6/6 (100%)
- **constraint**: baseline 10/10 (100%) · check 10/10 (100%)
- **all**: baseline 16/16 (100%) · check 16/16 (100%)

## Per-seed

- seed=2: baseline 8/8 (100%) · check 8/8 (100%)
- seed=3: baseline 8/8 (100%) · check 8/8 (100%)

## Matrix

| seed | prompt | condition | harness_ok | semantic/check_ok | rounds | notes |
|---|---|---|---|---|---|---|
| 2 | P02_edit_move_sphere | baseline | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.25, 0.00);CubeA=(0.00, 0.50, 0.00)` |
| 2 | P02_edit_move_sphere | check | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00);detail=SphereB_abo` |
| 2 | P03_edit_duplicate_row | baseline | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5` |
| 2 | P03_edit_duplicate_row | check | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5;detail=CubeC_spacing` |
| 2 | P09_edit_raise_sphere | baseline | ✅ | ✅ | 1 | `pass=True;y=2;SphereB=(1.50, 2.00, 0.00)` |
| 2 | P09_edit_raise_sphere | check | ✅ | ✅ | 1 | `pass=True;y=2;xz_ok=True;SphereB=(1.50, 2.00, 0.00);detail=SphereB_y_approx_2` |
| 2 | P04_constraint_left_of | baseline | ✅ | ✅ | 1 | `success=True passed=4 failed=0` |
| 2 | P04_constraint_left_of | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=4 failed=0 skipped=0 set=P04_left_of", "faile` |
| 2 | P05_constraint_on_top | baseline | ✅ | ✅ | 1 | `success=True passed=3 failed=0` |
| 2 | P05_constraint_on_top | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=3 failed=0 skipped=0 set=P05_on_top", "failed` |
| 2 | P06_constraint_distance | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 2 | P06_constraint_distance | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P06_distance", "fail` |
| 2 | P07_constraint_facing | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 2 | P07_constraint_facing | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P07_facing", "failed` |
| 2 | P08_constraint_no_overlap | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 2 | P08_constraint_no_overlap | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "fa` |
| 3 | P02_edit_move_sphere | baseline | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.25, 0.00);CubeA=(0.00, 0.50, 0.00)` |
| 3 | P02_edit_move_sphere | check | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00);detail=SphereB_abo` |
| 3 | P03_edit_duplicate_row | baseline | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5` |
| 3 | P03_edit_duplicate_row | check | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5;detail=CubeC_spacing` |
| 3 | P09_edit_raise_sphere | baseline | ✅ | ✅ | 1 | `pass=True;y=2;SphereB=(1.50, 2.00, 0.00)` |
| 3 | P09_edit_raise_sphere | check | ✅ | ✅ | 1 | `pass=True;y=2;xz_ok=True;SphereB=(1.50, 2.00, 0.00);detail=SphereB_y_approx_2` |
| 3 | P04_constraint_left_of | baseline | ✅ | ✅ | 1 | `success=True passed=4 failed=0` |
| 3 | P04_constraint_left_of | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=4 failed=0 skipped=0 set=P04_left_of", "faile` |
| 3 | P05_constraint_on_top | baseline | ✅ | ✅ | 1 | `success=True passed=3 failed=0` |
| 3 | P05_constraint_on_top | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=3 failed=0 skipped=0 set=P05_on_top", "failed` |
| 3 | P06_constraint_distance | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 3 | P06_constraint_distance | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P06_distance", "fail` |
| 3 | P07_constraint_facing | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 3 | P07_constraint_facing | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P07_facing", "failed` |
| 3 | P08_constraint_no_overlap | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| 3 | P08_constraint_no_overlap | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "fa` |

CSV: `results_formal_multiseed_qwen_20261021-155025.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_multiseed_qwen_20261021-154240/manifest.ndjson`

