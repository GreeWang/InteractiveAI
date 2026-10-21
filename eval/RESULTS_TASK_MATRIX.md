# Results — Scripted Task Matrix (12×3×A/B)

Updated: 2026-10-21T16:27:42+0800 Asia/Shanghai

Batch: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_task_matrix_20261021-161231`
Cells: **72**

Model fixed: qwen3.8-max. 12 prompts × seeds 1–3 × baseline/check.

## Aggregate by condition

| condition | success | rate | mean wall_ms | total tokens | mean cmds |
|-----------|---------|------|--------------|--------------|-----------|
| baseline | 36/36 | 100% | 12314 | 56574 | 4.0 |
| check | 36/36 | 100% | 12918 | 117626 | 2.0 |

## Per cell

| prompt | cond | seed | ok | rounds | cmds | wall_ms | tokens |
|--------|------|------|----|--------|------|---------|--------|
| P01_generate_table | baseline | 1 | ✅ | 1 | 6 | 14312 | 1770 |
| P01_generate_table | check | 1 | ✅ | 1 | 4 | 17425 | 4076 |
| P02_edit_move_sphere | baseline | 1 | ✅ | 1 | 3 | 9202 | 1393 |
| P02_edit_move_sphere | check | 1 | ✅ | 1 | 1 | 11717 | 3104 |
| P03_edit_duplicate_row | baseline | 1 | ✅ | 1 | 4 | 9202 | 1432 |
| P03_edit_duplicate_row | check | 1 | ✅ | 1 | 2 | 9421 | 2944 |
| P04_constraint_left_of | baseline | 1 | ✅ | 1 | 4 | 9908 | 1456 |
| P04_constraint_left_of | check | 1 | ✅ | 1 | 2 | 15911 | 3464 |
| P05_constraint_on_top | baseline | 1 | ✅ | 1 | 3 | 8412 | 1496 |
| P05_constraint_on_top | check | 1 | ✅ | 1 | 1 | 8124 | 3020 |
| P06_constraint_distance | baseline | 1 | ✅ | 1 | 4 | 15394 | 1737 |
| P06_constraint_distance | check | 1 | ✅ | 1 | 2 | 11336 | 3092 |
| P07_constraint_facing | baseline | 1 | ✅ | 1 | 3 | 16090 | 1729 |
| P07_constraint_facing | check | 1 | ✅ | 1 | 1 | 12227 | 3176 |
| P08_constraint_no_overlap | baseline | 1 | ✅ | 1 | 4 | 12898 | 1604 |
| P08_constraint_no_overlap | check | 1 | ✅ | 1 | 2 | 11528 | 3124 |
| P09_edit_raise_sphere | baseline | 1 | ✅ | 1 | 3 | 10499 | 1466 |
| P09_edit_raise_sphere | check | 1 | ✅ | 1 | 1 | 14823 | 3250 |
| P10_generate_row | baseline | 1 | ✅ | 1 | 8 | 10700 | 1595 |
| P10_generate_row | check | 1 | ✅ | 1 | 6 | 12222 | 3286 |
| P11_constraint_clearance | baseline | 1 | ✅ | 1 | 3 | 11403 | 1591 |
| P11_constraint_clearance | check | 1 | ✅ | 1 | 1 | 9227 | 3170 |
| P12_constraint_locked | baseline | 1 | ✅ | 1 | 3 | 13387 | 1673 |
| P12_constraint_locked | check | 1 | ✅ | 1 | 1 | 10427 | 3186 |
| P01_generate_table | baseline | 2 | ✅ | 1 | 6 | 11098 | 1632 |
| P01_generate_table | check | 2 | ✅ | 1 | 5 | 12428 | 3472 |
| P02_edit_move_sphere | baseline | 2 | ✅ | 1 | 3 | 9295 | 1359 |
| P02_edit_move_sphere | check | 2 | ✅ | 1 | 1 | 10603 | 3036 |
| P03_edit_duplicate_row | baseline | 2 | ✅ | 1 | 4 | 9228 | 1413 |
| P03_edit_duplicate_row | check | 2 | ✅ | 1 | 2 | 8413 | 2844 |
| P04_constraint_left_of | baseline | 2 | ✅ | 1 | 4 | 11522 | 1581 |
| P04_constraint_left_of | check | 2 | ✅ | 1 | 2 | 9805 | 3000 |
| P05_constraint_on_top | baseline | 2 | ✅ | 1 | 3 | 7958 | 1469 |
| P05_constraint_on_top | check | 2 | ✅ | 1 | 1 | 9672 | 3050 |
| P06_constraint_distance | baseline | 2 | ✅ | 1 | 4 | 10854 | 1474 |
| P06_constraint_distance | check | 2 | ✅ | 1 | 2 | 12019 | 3040 |
| P07_constraint_facing | baseline | 2 | ✅ | 1 | 3 | 18018 | 1647 |
| P07_constraint_facing | check | 2 | ✅ | 1 | 1 | 28975 | 4482 |
| P08_constraint_no_overlap | baseline | 2 | ✅ | 1 | 4 | 12047 | 1509 |
| P08_constraint_no_overlap | check | 2 | ✅ | 1 | 2 | 13479 | 3234 |
| P09_edit_raise_sphere | baseline | 2 | ✅ | 1 | 3 | 13762 | 1494 |
| P09_edit_raise_sphere | check | 2 | ✅ | 1 | 1 | 23697 | 4210 |
| P10_generate_row | baseline | 2 | ✅ | 1 | 8 | 12428 | 1578 |
| P10_generate_row | check | 2 | ✅ | 1 | 6 | 11088 | 3236 |
| P11_constraint_clearance | baseline | 2 | ✅ | 1 | 3 | 13251 | 1649 |
| P11_constraint_clearance | check | 2 | ✅ | 1 | 1 | 11373 | 3138 |
| P12_constraint_locked | baseline | 2 | ✅ | 1 | 3 | 11533 | 1576 |
| P12_constraint_locked | check | 2 | ✅ | 1 | 1 | 13091 | 3296 |
| P01_generate_table | baseline | 3 | ✅ | 1 | 6 | 16736 | 1814 |
| P01_generate_table | check | 3 | ✅ | 1 | 4 | 15489 | 3560 |
| P02_edit_move_sphere | baseline | 3 | ✅ | 1 | 3 | 9629 | 1369 |
| P02_edit_move_sphere | check | 3 | ✅ | 1 | 1 | 11798 | 3020 |
| P03_edit_duplicate_row | baseline | 3 | ✅ | 1 | 4 | 13336 | 1559 |
| P03_edit_duplicate_row | check | 3 | ✅ | 1 | 2 | 11474 | 3102 |
| P04_constraint_left_of | baseline | 3 | ✅ | 1 | 4 | 10860 | 1522 |
| P04_constraint_left_of | check | 3 | ✅ | 1 | 2 | 10372 | 2992 |
| P05_constraint_on_top | baseline | 3 | ✅ | 1 | 3 | 10564 | 1534 |
| P05_constraint_on_top | check | 3 | ✅ | 1 | 1 | 9775 | 3018 |
| P06_constraint_distance | baseline | 3 | ✅ | 1 | 4 | 18354 | 1797 |
| P06_constraint_distance | check | 3 | ✅ | 1 | 2 | 17178 | 3548 |
| P07_constraint_facing | baseline | 3 | ✅ | 1 | 3 | 13454 | 1569 |
| P07_constraint_facing | check | 3 | ✅ | 1 | 1 | 15778 | 3290 |
| P08_constraint_no_overlap | baseline | 3 | ✅ | 1 | 4 | 10951 | 1455 |
| P08_constraint_no_overlap | check | 3 | ✅ | 1 | 2 | 13275 | 3208 |
| P09_edit_raise_sphere | baseline | 3 | ✅ | 1 | 3 | 23764 | 1946 |
| P09_edit_raise_sphere | check | 3 | ✅ | 1 | 1 | 14872 | 3208 |
| P10_generate_row | baseline | 3 | ✅ | 1 | 8 | 11353 | 1589 |
| P10_generate_row | check | 3 | ✅ | 1 | 6 | 11877 | 3252 |
| P11_constraint_clearance | baseline | 3 | ✅ | 1 | 3 | 10262 | 1523 |
| P11_constraint_clearance | check | 3 | ✅ | 1 | 1 | 11671 | 3200 |
| P12_constraint_locked | baseline | 3 | ✅ | 1 | 3 | 11657 | 1574 |
| P12_constraint_locked | check | 3 | ✅ | 1 | 1 | 12472 | 3298 |

## Failures (0)

None.
