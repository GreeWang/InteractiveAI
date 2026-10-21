# Formal Formative Round 2 (Bailian / Qwen)

Updated: 2026-10-21T15:32:22+08:00 Asia/Shanghai (UTC+8) — **includes dirty-cell retries**
Original batch: `batch_formal_r2_20261021-143620`
Retry batch: `batch_formal_r2_retry_20261021-153116`
Model: **qwen3.8-max** · seeds=**1** · check max_rounds=**3**
Prompts: **P02–P09** (generate → see R3).

## Aggregate success (semantic / ConstraintChecker)

| Slice | baseline | check (multiturn) |
|---|---|---|
| Edit (P02/P03/P09) | 3/3 (100%) | 3/3 (100%) |
| Constraint (P04–P08) | 4/5 (80%) | 5/5 (100%) |
| All | 7/8 (88%) | 8/8 (100%) |

Harness OK — baseline 8/8 (100%) · check 8/8 (100%)

## Matrix

| prompt | condition | harness_ok | semantic/check_ok | rounds | retried | notes |
|---|---|---|---|---|---|---|
| P02_edit_move_sphere | baseline | ✅ | ✅ | 1 |  | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00)` |
| P02_edit_move_sphere | check | ✅ | ✅ | 1 |  | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00);detail=SphereB_abo` |
| P03_edit_duplicate_row | baseline | ✅ | ✅ | 1 |  | `pass=True;exists=True;dist=1.5` |
| P03_edit_duplicate_row | check | ✅ | ✅ | 1 |  | `pass=True;exists=True;dist=1.5;detail=CubeC_spacing` |
| P09_edit_raise_sphere | baseline | ✅ | ✅ | 1 |  | `pass=True;y=2;SphereB=(1.50, 2.00, 0.00)` |
| P09_edit_raise_sphere | check | ✅ | ✅ | 1 |  | `pass=True;y=2;xz_ok=True;SphereB=(1.50, 2.00, 0.00);detail=SphereB_y_approx_2` |
| P04_constraint_left_of | baseline | ✅ | ✅ | 1 |  | `success=True passed=4 failed=0` |
| P04_constraint_left_of | check | ✅ | ✅ | 1 |  | `{"eval_snip": "success=True passed=4 failed=0 skipped=0 set=P04_left_of", "faile` |
| P05_constraint_on_top | baseline | ✅ | ❌ | 1 |  | `success=False passed=2 failed=1` |
| P05_constraint_on_top | check | ✅ | ✅ | 1 | yes | `{"eval_snip": "success=True passed=3 failed=0 skipped=0 set=P05_on_top", "failed` |
| P06_constraint_distance | baseline | ✅ | ✅ | 1 |  | `success=True passed=1 failed=0` |
| P06_constraint_distance | check | ✅ | ✅ | 1 |  | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P06_distance", "fail` |
| P07_constraint_facing | baseline | ✅ | ✅ | 1 |  | `success=True passed=1 failed=0` |
| P07_constraint_facing | check | ✅ | ✅ | 1 |  | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P07_facing", "failed` |
| P08_constraint_no_overlap | baseline | ✅ | ✅ | 1 |  | `success=True passed=1 failed=0` |
| P08_constraint_no_overlap | check | ✅ | ✅ | 1 | yes | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "fa` |

## Retry audit

- **P05_constraint_on_top check**: before=False → after=True
  - before notes: `llm_error:Remote end closed connection without response`
  - after notes: `{"eval_snip": "success=True passed=3 failed=0 skipped=0 set=P05_on_top", "failed_constraints": [], "failed_messages": [], "current_poses": "RedBox|pos=-1.5,0.5,0;BlueBall|pos=1.5,0.5,0;CupOnBox|pos=-1`
- **P08_constraint_no_overlap check**: before=False → after=True
  - before notes: `llm_error:The read operation timed out`
  - after notes: `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P08_no_overlap", "failed_constraints": [], "failed_messages": [], "current_poses": "RedBox|pos=-1.5,0.5,0;BlueBall|pos=1.5,0.5,0;CupOnBox|po`

CSV: `results_formal_r2_20261021-153222.csv`
Retry audit JSON: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_r2_retry_20261021-153116/retry_audit.json`

## Protocol notes

- R2: Bailian/DashScope `qwen3.8-max`.
- Dirty cells (API timeout / disconnect) retried after P05 prompt harden.
- P05 cells now prep CupOnBox to `[0,0.5,0]` so on_top is a real placement task.


## P05 baseline after harden (smoke, not yet merged into matrix above)

Original R2 P05 **baseline** remains ❌ in the matrix (pre-harden plan used `[0,1.5,0]`).
Post-harden smokes (same model `qwen3.8-max` / also `deepseek-v4-pro`) place CupOnBox at `[-1.5,1.25,0]` and **pass** ConstraintChecker in 1 shot — see `eval/P05_HARDEN_EVIDENCE.md`.
A formal P05 baseline re-score can be merged when the closeout chain is idle.

