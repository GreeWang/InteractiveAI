# Results — Skill-only Ablation (6 briefs × 3 arms)

Updated: 2026-10-21T16:49:41+0800 Asia/Shanghai

Batch: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_ablation_20261021-164519`
Cells: **18**

Arms: baseline (ordinary prompt), skill (richer prompt, no Check loop), check (multiturn ≤3). Seed=1. Model: qwen3.8-max.

## Aggregate by condition

| condition | success | rate | mean wall_ms | total tokens | mean cmds |
|-----------|---------|------|--------------|--------------|-----------|
| baseline | 6/6 | 100% | 14494 | 9656 | 3.7 |
| check | 6/6 | 100% | 13742 | 19528 | 1.7 |
| skill | 6/6 | 100% | 15410 | 10810 | 3.7 |

## Per cell

| prompt | cond | seed | ok | rounds | cmds | wall_ms | tokens |
|--------|------|------|----|--------|------|---------|--------|
| P02_edit_move_sphere | baseline | 1 | ✅ | 1 | 3 | 10670 | 1411 |
| P02_edit_move_sphere | skill | 1 | ✅ | 1 | 3 | 9158 | 1480 |
| P02_edit_move_sphere | check | 1 | ✅ | 1 | 1 | 15570 | 3334 |
| P05_constraint_on_top | baseline | 1 | ✅ | 1 | 3 | 11562 | 1513 |
| P05_constraint_on_top | skill | 1 | ✅ | 1 | 3 | 11171 | 1671 |
| P05_constraint_on_top | check | 1 | ✅ | 1 | 1 | 10473 | 2986 |
| P08_constraint_no_overlap | baseline | 1 | ✅ | 1 | 4 | 18960 | 1641 |
| P08_constraint_no_overlap | skill | 1 | ✅ | 1 | 4 | 17441 | 1838 |
| P08_constraint_no_overlap | check | 1 | ✅ | 1 | 2 | 12291 | 3010 |
| P11_constraint_clearance | baseline | 1 | ✅ | 1 | 3 | 13259 | 1598 |
| P11_constraint_clearance | skill | 1 | ✅ | 1 | 3 | 16663 | 1792 |
| P11_constraint_clearance | check | 1 | ✅ | 1 | 1 | 13379 | 3296 |
| P01_generate_table | baseline | 1 | ✅ | 1 | 6 | 19852 | 1883 |
| P01_generate_table | skill | 1 | ✅ | 1 | 6 | 26066 | 2348 |
| P01_generate_table | check | 1 | ✅ | 1 | 4 | 16073 | 3504 |
| P12_constraint_locked | baseline | 1 | ✅ | 1 | 3 | 12665 | 1610 |
| P12_constraint_locked | skill | 1 | ✅ | 1 | 3 | 11963 | 1681 |
| P12_constraint_locked | check | 1 | ✅ | 1 | 1 | 14668 | 3398 |

## Failures (0)

None.
