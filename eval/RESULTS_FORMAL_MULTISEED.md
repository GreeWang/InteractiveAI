# Formal multi-seed summary (P02–P09)

Updated: 2026-10-21T15:51:32+08:00 Asia/Shanghai (UTC+8)
Seeds present: **[1, 2, 3]** · models: [('bailian', 'qwen3.8-max'), ('deepseek', 'deepseek-v4-pro')]
Seed 1 reused from R1 (DeepSeek) / R2 (Qwen, with dirty-cell retry). Seeds 2–3 from `run_formal_multiseed.sh`.

## Pooled rates

- **qwen3.8-max**: baseline 24/24 (100%) · check 24/24 (100%) · n=48
- **deepseek-v4-pro**: baseline 22/24 (92%) · check 23/24 (96%) · n=48

## Per seed × model

- seed=1 · qwen3.8-max: baseline 8/8 (100%) · check 8/8 (100%)
- seed=1 · deepseek-v4-pro: baseline 7/8 (88%) · check 7/8 (88%)
- seed=2 · qwen3.8-max: baseline 8/8 (100%) · check 8/8 (100%)
- seed=2 · deepseek-v4-pro: baseline 7/8 (88%) · check 8/8 (100%)
- seed=3 · qwen3.8-max: baseline 8/8 (100%) · check 8/8 (100%)
- seed=3 · deepseek-v4-pro: baseline 8/8 (100%) · check 8/8 (100%)

## Matrix (compact failures)

| model | seed | prompt | condition | ok | notes |
|---|---|---|---|---|---|
| deepseek-v4-pro | 1 | P05_constraint_on_top | baseline | ❌ | `success=False passed=2 failed=1` |
| deepseek-v4-pro | 1 | P05_constraint_on_top | check | ❌ | `{"eval_snip": "success=False passed=2 failed=1 skipped=0 set` |
| deepseek-v4-pro | 2 | P09_edit_raise_sphere | baseline | ❌ | `pass=False;y=0.5;SphereB=(1.50, 0.50, 0.00)` |

CSV: `results_formal_multiseed_20261021-155132.csv`
Rows: 96

## Full matrix

| model | seed | prompt | condition | ok | rounds |
|---|---|---|---|---|---|
| deepseek-v4-pro | 1 | P02_edit_move_sphere | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P02_edit_move_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P03_edit_duplicate_row | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P09_edit_raise_sphere | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P09_edit_raise_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P04_constraint_left_of | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P04_constraint_left_of | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P05_constraint_on_top | baseline | ❌ | 1 |
| deepseek-v4-pro | 1 | P05_constraint_on_top | check | ❌ | 3 |
| deepseek-v4-pro | 1 | P06_constraint_distance | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P06_constraint_distance | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P07_constraint_facing | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P07_constraint_facing | check | ✅ | 1 |
| deepseek-v4-pro | 1 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| deepseek-v4-pro | 1 | P08_constraint_no_overlap | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P02_edit_move_sphere | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P02_edit_move_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P03_edit_duplicate_row | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P09_edit_raise_sphere | baseline | ❌ | 1 |
| deepseek-v4-pro | 2 | P09_edit_raise_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P04_constraint_left_of | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P04_constraint_left_of | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P05_constraint_on_top | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P05_constraint_on_top | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P06_constraint_distance | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P06_constraint_distance | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P07_constraint_facing | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P07_constraint_facing | check | ✅ | 1 |
| deepseek-v4-pro | 2 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| deepseek-v4-pro | 2 | P08_constraint_no_overlap | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P02_edit_move_sphere | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P02_edit_move_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P03_edit_duplicate_row | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P09_edit_raise_sphere | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P09_edit_raise_sphere | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P04_constraint_left_of | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P04_constraint_left_of | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P05_constraint_on_top | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P05_constraint_on_top | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P06_constraint_distance | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P06_constraint_distance | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P07_constraint_facing | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P07_constraint_facing | check | ✅ | 1 |
| deepseek-v4-pro | 3 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| deepseek-v4-pro | 3 | P08_constraint_no_overlap | check | ✅ | 1 |
| qwen3.8-max | 1 | P02_edit_move_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P02_edit_move_sphere | check | ✅ | 1 |
| qwen3.8-max | 1 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P03_edit_duplicate_row | check | ✅ | 1 |
| qwen3.8-max | 1 | P09_edit_raise_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P09_edit_raise_sphere | check | ✅ | 1 |
| qwen3.8-max | 1 | P04_constraint_left_of | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P04_constraint_left_of | check | ✅ | 1 |
| qwen3.8-max | 1 | P05_constraint_on_top | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P05_constraint_on_top | check | ✅ | 1 |
| qwen3.8-max | 1 | P06_constraint_distance | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P06_constraint_distance | check | ✅ | 1 |
| qwen3.8-max | 1 | P07_constraint_facing | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P07_constraint_facing | check | ✅ | 1 |
| qwen3.8-max | 1 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| qwen3.8-max | 1 | P08_constraint_no_overlap | check | ✅ | 1 |
| qwen3.8-max | 2 | P02_edit_move_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P02_edit_move_sphere | check | ✅ | 1 |
| qwen3.8-max | 2 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P03_edit_duplicate_row | check | ✅ | 1 |
| qwen3.8-max | 2 | P09_edit_raise_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P09_edit_raise_sphere | check | ✅ | 1 |
| qwen3.8-max | 2 | P04_constraint_left_of | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P04_constraint_left_of | check | ✅ | 1 |
| qwen3.8-max | 2 | P05_constraint_on_top | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P05_constraint_on_top | check | ✅ | 1 |
| qwen3.8-max | 2 | P06_constraint_distance | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P06_constraint_distance | check | ✅ | 1 |
| qwen3.8-max | 2 | P07_constraint_facing | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P07_constraint_facing | check | ✅ | 1 |
| qwen3.8-max | 2 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| qwen3.8-max | 2 | P08_constraint_no_overlap | check | ✅ | 1 |
| qwen3.8-max | 3 | P02_edit_move_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P02_edit_move_sphere | check | ✅ | 1 |
| qwen3.8-max | 3 | P03_edit_duplicate_row | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P03_edit_duplicate_row | check | ✅ | 1 |
| qwen3.8-max | 3 | P09_edit_raise_sphere | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P09_edit_raise_sphere | check | ✅ | 1 |
| qwen3.8-max | 3 | P04_constraint_left_of | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P04_constraint_left_of | check | ✅ | 1 |
| qwen3.8-max | 3 | P05_constraint_on_top | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P05_constraint_on_top | check | ✅ | 1 |
| qwen3.8-max | 3 | P06_constraint_distance | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P06_constraint_distance | check | ✅ | 1 |
| qwen3.8-max | 3 | P07_constraint_facing | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P07_constraint_facing | check | ✅ | 1 |
| qwen3.8-max | 3 | P08_constraint_no_overlap | baseline | ✅ | 1 |
| qwen3.8-max | 3 | P08_constraint_no_overlap | check | ✅ | 1 |
