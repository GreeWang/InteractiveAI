# Prompt2Scene LLM Multi-turn Check Results

Updated: 2026-10-20T10:24:56+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_llm_multiturn_20261020-102120`
Model: **deepseek-v4-pro** · max_rounds=3

Harness: `condition=check` → `llm_multiturn.py` (plan → execute → verify → repair).
Edit prompts use semantic postcheck; F03 uses ConstraintChecker.

## Summary

| Metric | Count |
|---|---|
| Prompts | 4 |
| Final pass | 4/4 |
| Needed repair (>1 round) | 0 |

## vs previous single-shot LLM batch

| prompt | previous | this multiturn |
|---|---|---|
| P02_edit_move_sphere | prev single-shot semantic ✅ | ✅ rounds=1 |
| P03_edit_duplicate_row | prev single-shot semantic ❌ dist≈2.69 | ✅ rounds=1 |
| P09_edit_raise_sphere | prev single-shot semantic ❌ self-revert | ✅ rounds=1 |
| P04_constraint_left_of | prev check ✅ | ✅ rounds=1 |

## Per-prompt

| prompt_id | final_pass | rounds | verify report (last) |
|---|---|---|---|
| P02_edit_move_sphere | ✅ | 1 | `pass=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00);detail=SphereB_above_CubeA` |
| P03_edit_duplicate_row | ✅ | 1 | `pass=True;exists=True;dist=1.5;detail=CubeC_spacing` |
| P09_edit_raise_sphere | ✅ | 1 | `pass=True;y=2;xz_ok=True;SphereB=(1.50, 2.00, 0.00);detail=SphereB_y_approx_2` |
| P04_constraint_left_of | ✅ | 1 | `{"eval_snip": "success=True passed=4 failed=0 skipped=0 set=P04_left_of", "failed_constrai` |

CSV: `results_llm_multiturn_20261020-102456.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_llm_multiturn_20261020-102120/manifest.ndjson`

## Implementation notes

- New: `eval/scripts/llm_multiturn.py`; `llm_run.sh … check [--max-rounds N]`
- Round logs under `round_XX/plan.json`, `verify.json`, `llm_response.json`
- System prompt: no self-restore; spacing 1.2–1.8 for P03
- Fixtures restored after each prompt

