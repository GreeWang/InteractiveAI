# Prompt2Scene Formative A/B Results

Updated: 2026-10-18T10:05:37+08:00 (Asia/Shanghai)

**Honest scope:** `baseline_cli` = Unity CLI edit smoke (no LLM). `check_cli` = ConstraintChecker on seeded F03. `none` = generate prompts not automated yet.

CSV: `results_ab_20261018-100537.csv`

| prompt_id | phase | fixture | condition | automation | success | status | passed/failed | run_folder |
|---|---|---|---|---|---|---|---|---|
| P01_generate_table | generate | F01 | n/a | none | False | not_automated |  | `` |
| P02_edit_move_sphere | edit | F02 | baseline | baseline_cli | True | ok |  | `~/Projects/Prompt2Scene/eval/runs/20261018-100526_P02_edit_move_sphere_baseline` |
| P03_edit_duplicate_row | edit | F02 | baseline | baseline_cli | True | ok |  | `~/Projects/Prompt2Scene/eval/runs/20261018-100528_P03_edit_duplicate_row_baseline` |
| P04_constraint_left_of | constraint | F03 | check | check_cli | True | ok | 4/0 | `~/Projects/Prompt2Scene/eval/runs/20261018-100530_P04_constraint_left_of_check` |
| P05_constraint_on_top | constraint | F03 | check | check_cli | True | ok | 3/0 | `~/Projects/Prompt2Scene/eval/runs/20261018-100532_P05_constraint_on_top_check` |
| P06_constraint_distance | constraint | F03 | check | check_cli | True | ok | 1/0 | `~/Projects/Prompt2Scene/eval/runs/20261018-100533_P06_constraint_distance_check` |
| P07_constraint_facing | constraint | F03 | check | check_cli | True | ok | 1/0 | `~/Projects/Prompt2Scene/eval/runs/20261018-100534_P07_constraint_facing_check` |
| P08_constraint_no_overlap | constraint | F03 | check | check_cli | True | ok | 1/0 | `~/Projects/Prompt2Scene/eval/runs/20261018-100535_P08_constraint_no_overlap_check` |
| P09_edit_raise_sphere | edit | F02 | baseline | baseline_cli | True | ok |  | `~/Projects/Prompt2Scene/eval/runs/20261018-100536_P09_edit_raise_sphere_baseline` |
| P10_generate_row | generate | F01 | n/a | none | False | not_automated |  | `` |

## Counts
- Prompts total: 10
- Automated success: 8
- Failed: 0
- Not automated: 2
- Missing run: 0
