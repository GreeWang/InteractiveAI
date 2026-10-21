# Results — Held-out A/B (12 briefs)

Updated: 2026-10-21T16:45:18+0800 Asia/Shanghai

Batch: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_heldout_ab_20261021-162742`
Cells: **72**

Shortfall vs proposal 24 briefs: ran **12** held-out × 3 seeds × A/B (72 cells) to control API cost/time. Model fixed: qwen3.8-max.

## Aggregate by condition

| condition | success | rate | mean wall_ms | total tokens | mean cmds |
|-----------|---------|------|--------------|--------------|-----------|
| baseline | 33/36 | 92% | 14162 | 56699 | 3.9 |
| check | 36/36 | 100% | 15112 | 121694 | 2.1 |

## Per cell

| prompt | cond | seed | ok | rounds | cmds | wall_ms | tokens |
|--------|------|------|----|--------|------|---------|--------|
| H01_gen_desk_mug | baseline | 1 | ✅ | 1 | 6 | 20575 | 1975 |
| H01_gen_desk_mug | check | 1 | ✅ | 1 | 4 | 12784 | 3264 |
| H02_edit_sphere_stack | baseline | 1 | ✅ | 1 | 3 | 9761 | 1346 |
| H02_edit_sphere_stack | check | 1 | ✅ | 1 | 1 | 8668 | 2724 |
| H03_edit_side_cube | baseline | 1 | ✅ | 1 | 4 | 10865 | 1447 |
| H03_edit_side_cube | check | 1 | ✅ | 1 | 2 | 12167 | 3140 |
| H04_left_same_y | baseline | 1 | ✅ | 1 | 4 | 16065 | 1696 |
| H04_left_same_y | check | 1 | ✅ | 1 | 2 | 18571 | 3632 |
| H05_cup_stack | baseline | 1 | ✅ | 1 | 3 | 8862 | 1316 |
| H05_cup_stack | check | 1 | ✅ | 1 | 1 | 10972 | 2724 |
| H06_spacing_band | baseline | 1 | ✅ | 1 | 4 | 16459 | 1715 |
| H06_spacing_band | check | 1 | ✅ | 1 | 2 | 15672 | 3160 |
| H07_face_neighbor | baseline | 1 | ✅ | 1 | 3 | 21665 | 1894 |
| H07_face_neighbor | check | 1 | ✅ | 1 | 1 | 18269 | 3348 |
| H08_no_penetrate | baseline | 1 | ✅ | 1 | 4 | 14161 | 1565 |
| H08_no_penetrate | check | 1 | ✅ | 1 | 2 | 15971 | 3366 |
| H09_lift_sphere | baseline | 1 | ✅ | 1 | 3 | 8260 | 1302 |
| H09_lift_sphere | check | 1 | ✅ | 1 | 1 | 7171 | 2614 |
| H10_row_xyz | baseline | 1 | ✅ | 1 | 8 | 13663 | 1579 |
| H10_row_xyz | check | 1 | ✅ | 1 | 6 | 12468 | 3250 |
| H11_keepout | baseline | 1 | ✅ | 1 | 3 | 12764 | 1474 |
| H11_keepout | check | 1 | ✅ | 1 | 1 | 12867 | 3044 |
| H12_preserve_red | baseline | 1 | ❌ | 1 | 3 | 18466 | 1841 |
| H12_preserve_red | check | 1 | ✅ | 2 | 2 | 44273 | 7126 |
| H01_gen_desk_mug | baseline | 2 | ✅ | 1 | 6 | 12158 | 1573 |
| H01_gen_desk_mug | check | 2 | ✅ | 1 | 4 | 11870 | 3202 |
| H02_edit_sphere_stack | baseline | 2 | ✅ | 1 | 3 | 10158 | 1414 |
| H02_edit_sphere_stack | check | 2 | ✅ | 1 | 1 | 11468 | 2800 |
| H03_edit_side_cube | baseline | 2 | ✅ | 1 | 4 | 9367 | 1385 |
| H03_edit_side_cube | check | 2 | ✅ | 1 | 2 | 10171 | 2836 |
| H04_left_same_y | baseline | 2 | ✅ | 1 | 3 | 15068 | 1646 |
| H04_left_same_y | check | 2 | ✅ | 1 | 1 | 11964 | 3038 |
| H05_cup_stack | baseline | 2 | ✅ | 1 | 3 | 9467 | 1347 |
| H05_cup_stack | check | 2 | ✅ | 1 | 1 | 10166 | 2802 |
| H06_spacing_band | baseline | 2 | ✅ | 1 | 4 | 12958 | 1523 |
| H06_spacing_band | check | 2 | ✅ | 1 | 2 | 11275 | 2962 |
| H07_face_neighbor | baseline | 2 | ✅ | 1 | 3 | 19558 | 1776 |
| H07_face_neighbor | check | 2 | ✅ | 1 | 1 | 11672 | 2932 |
| H08_no_penetrate | baseline | 2 | ✅ | 1 | 4 | 15359 | 1604 |
| H08_no_penetrate | check | 2 | ✅ | 1 | 2 | 22574 | 3954 |
| H09_lift_sphere | baseline | 2 | ✅ | 1 | 3 | 7463 | 1283 |
| H09_lift_sphere | check | 2 | ✅ | 1 | 1 | 9268 | 2608 |
| H10_row_xyz | baseline | 2 | ✅ | 1 | 8 | 12056 | 1517 |
| H10_row_xyz | check | 2 | ✅ | 1 | 6 | 11780 | 3178 |
| H11_keepout | baseline | 2 | ✅ | 1 | 3 | 14361 | 1474 |
| H11_keepout | check | 2 | ✅ | 1 | 1 | 12578 | 3048 |
| H12_preserve_red | baseline | 2 | ❌ | 1 | 3 | 38363 | 2699 |
| H12_preserve_red | check | 2 | ✅ | 2 | 2 | 36670 | 6428 |
| H01_gen_desk_mug | baseline | 3 | ✅ | 1 | 6 | 13957 | 1641 |
| H01_gen_desk_mug | check | 3 | ✅ | 1 | 4 | 13264 | 3374 |
| H02_edit_sphere_stack | baseline | 3 | ✅ | 1 | 3 | 9364 | 1361 |
| H02_edit_sphere_stack | check | 3 | ✅ | 1 | 1 | 8069 | 2684 |
| H03_edit_side_cube | baseline | 3 | ✅ | 1 | 4 | 10062 | 1369 |
| H03_edit_side_cube | check | 3 | ✅ | 1 | 2 | 10370 | 2878 |
| H04_left_same_y | baseline | 3 | ✅ | 1 | 3 | 16166 | 1655 |
| H04_left_same_y | check | 3 | ✅ | 1 | 1 | 13275 | 3100 |
| H05_cup_stack | baseline | 3 | ✅ | 1 | 3 | 11656 | 1419 |
| H05_cup_stack | check | 3 | ✅ | 1 | 1 | 9275 | 2710 |
| H06_spacing_band | baseline | 3 | ✅ | 1 | 4 | 15455 | 1566 |
| H06_spacing_band | check | 3 | ✅ | 1 | 2 | 15074 | 3226 |
| H07_face_neighbor | baseline | 3 | ✅ | 1 | 3 | 17464 | 1655 |
| H07_face_neighbor | check | 3 | ✅ | 1 | 1 | 17570 | 3420 |
| H08_no_penetrate | baseline | 3 | ✅ | 1 | 4 | 11160 | 1406 |
| H08_no_penetrate | check | 3 | ✅ | 1 | 2 | 24868 | 3894 |
| H09_lift_sphere | baseline | 3 | ✅ | 1 | 3 | 8866 | 1297 |
| H09_lift_sphere | check | 3 | ✅ | 1 | 1 | 8668 | 2674 |
| H10_row_xyz | baseline | 3 | ✅ | 1 | 8 | 13561 | 1572 |
| H10_row_xyz | check | 3 | ✅ | 1 | 6 | 11874 | 3122 |
| H11_keepout | baseline | 3 | ✅ | 1 | 3 | 14864 | 1524 |
| H11_keepout | check | 3 | ✅ | 1 | 1 | 14772 | 3066 |
| H12_preserve_red | baseline | 3 | ❌ | 1 | 3 | 19358 | 1843 |
| H12_preserve_red | check | 3 | ✅ | 2 | 3 | 35675 | 6366 |

## Failures (3)

- `H12_preserve_red` / baseline / seed=1: success=False passed=4 failed=1
- `H12_preserve_red` / baseline / seed=2: success=False passed=4 failed=1
- `H12_preserve_red` / baseline / seed=3: success=False passed=4 failed=1
