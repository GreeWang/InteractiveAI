# Formal Formative Round 2 (Bailian / Qwen)

Updated: 2026-10-21T15:17:57+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_formal_r2_20261021-143620`
Model: **qwen3.8-max** only · seeds=**1** per cell · check max_rounds=**3**
Prompts: **P02–P09** (P01/P10 generate deferred).

## Aggregate success (semantic / ConstraintChecker)

| Slice | baseline | check (multiturn) |
|---|---|---|
| Edit (P02/P03/P09) | 3/3 (100%) | 3/3 (100%) |
| Constraint (P04–P08) | 4/5 (80%) | 3/5 (60%) |
| All | 7/8 (88%) | 6/8 (75%) |

Harness OK — baseline 8/8 (100%) · check 6/8 (75%)

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
| P05_constraint_on_top | check | ❌ | ❌ | 2 | `llm_error:Remote end closed connection without response` |
| P06_constraint_distance | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P06_constraint_distance | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P06_distance", "fail` |
| P07_constraint_facing | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P07_constraint_facing | check | ✅ | ✅ | 1 | `{"eval_snip": "success=True passed=1 failed=0 skipped=0 set=P07_facing", "failed` |
| P08_constraint_no_overlap | baseline | ✅ | ✅ | 1 | `success=True passed=1 failed=0` |
| P08_constraint_no_overlap | check | ❌ | ❌ | 1 | `llm_error:The read operation timed out` |

CSV: `results_formal_r2_20261021-151757.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_r2_20261021-143620/manifest.ndjson`


## Unique failures

1. **P05_constraint_on_top** (baseline ❌ / check ❌)
   - Semantic: same as R1 — `on_top_of` fails with `XZ offset=1.5 > max_horizontal=0.5` (model places CupOnBox at `[0,1.5,0]` without reading RedBox XZ).
   - Check aborted early at round **2/3** with Bailian transport error: `Remote end closed connection without response` (after round-1 still failing the XZ check).

2. **P08_constraint_no_overlap** check only (baseline ✅ / check ❌)
   - Not a semantic miss: first LLM call timed out (`The read operation timed out`, 300s). No plan executed. Baseline for the same prompt passed in 1 shot.

Transport note: Bailian latency was uneven this run (e.g. P07 check ~5 min before responding). Failures above mix one hard constraint miss (P05) with API flakes (P05 r2, P08 check).

## Protocol notes

- R2: Bailian/DashScope `qwen3.8-max` (second model family vs R1 deepseek-v4-pro).
- `baseline` = single-shot LLM→CLI; scored by postcheck / ConstraintChecker after execute.
- `check` = multiturn repair up to 3 rounds (`llm_multiturn.py`).
- Fixtures restored between cells; generate prompts P01/P10 deferred.

