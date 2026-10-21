# Formal Formative Round 1 (minimal)

Updated: 2026-10-20T10:50:43+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_formal_r1_20261020-102933`
Model: **deepseek-v4-pro** only · seeds=**1** per cell · check max_rounds=**3**
Prompts: **P02–P09** (P01/P10 generate deferred).

## Aggregate success (semantic / ConstraintChecker)

| Slice | baseline | check (multiturn) |
|---|---|---|
| Edit (P02/P03/P09) | 3/3 (100%) | 3/3 (100%) |
| Constraint (P04–P08) | 4/5 (80%) | 4/5 (80%) |
| All | 7/8 (88%) | 7/8 (88%) |

Harness OK — baseline 8/8 (100%) · check 7/8 (88%)

## Matrix

| prompt | condition | harness_ok | semantic/check_ok | rounds | notes |
|---|---|---|---|---|---|
| P02_edit_move_sphere | baseline | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00)` |
| P02_edit_move_sphere | check | ✅ | ✅ | 1 | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00);detail=SphereB_abo` |
| P03_edit_duplicate_row | baseline | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5` |
| P03_edit_duplicate_row | check | ✅ | ✅ | 1 | `pass=True;exists=True;dist=1.5;detail=CubeC_spacing` |
| P09_edit_raise_sphere | baseline | ✅ | ✅ | 1 | `pass=True;y=2;SphereB=(1.50, 2.00, 0.00)` |
| P09_edit_raise_sphere | check | ✅ | ✅ | 1 | `pass=True;y=2;xz_ok=True;SphereB=(1.50, 2.00, 0.00);detail=SphereB_y_approx_2` |
| P04_constraint_left_of | baseline | ✅ | ✅ | 1 | `success=True passed=4 failed=0` |
| P04_constraint_left_of | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=4 failed=0 skipped=0 set=P04_left_of", "faile` |
| P05_constraint_on_top | baseline | ✅ | ❌ | 1 | `success=False passed=2 failed=1` |
| P05_constraint_on_top | check | ❌ | ❌ | 3 | `{"eval_snip": "success=False passed=2 failed=1 skipped=0 set=P05_on_top", "faile` |
| P06_constraint_distance | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P06_constraint_distance | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P06_distance", "fail` |
| P07_constraint_facing | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P07_constraint_facing | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P07_facing", "failed` |
| P08_constraint_no_overlap | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P08_constraint_no_overlap | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "fa` |

CSV: `results_formal_r1_20261020-105043.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_r1_20261020-102933/manifest.ndjson`

## Protocol notes

- R1 minimal: DeepSeek only (`deepseek-v4-pro`); no second model family.
- `baseline` = single-shot LLM→CLI; scored by postcheck / ConstraintChecker after execute.
- `check` = multiturn repair up to 3 rounds (`llm_multiturn.py`).
- Fixtures restored between cells; generate prompts P01/P10 deferred.


## Post-hoc: P05 after harden (2026-10-21)

R1 numbers above are **historical** (pre-harden). After system/prompt harden + CupOnBox prep,
`deepseek-v4-pro` P05 baseline/check both pass in 1 round — see `eval/P05_HARDEN_EVIDENCE.md`.
Checker thresholds were **not** loosened.

