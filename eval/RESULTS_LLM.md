# Prompt2Scene LLM Formative Batch Results

Updated: 2026-10-20T10:17:45+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_llm_20261020-100417`
Model: **deepseek-v4-pro**

This table is for **LLM → Unity CLI** runs (`llm_run.sh`), distinct from the earlier CLI-only A/B (`RESULTS_AB.md`).

## Summary

| Metric | Count |
|---|---|
| Prompts ran | 8 |
| Harness success (commands/API) | 6/8 |
| Semantic / Check pass | 6/8 |
| Edit baseline semantic pass | 1/3 |
| Constraint check pass | 5/5 |

## Per-prompt

| prompt_id | condition | harness | semantic/check | n_cmds | notes |
|---|---|---|---|---|---|
| P02_edit_move_sphere | baseline | ✅ | ✅ | 1 | above=True;SphereB=(0.00, 1.50, 0.00);CubeA=(0.00, 0.50, 0.00) |
| P03_edit_duplicate_row | baseline | ✅ | ❌ | 2 | exists=True;dist=2.692582;ok=False |
| P09_edit_raise_sphere | baseline | ✅ | ❌ | 3 | y=1.5;ok=False;SphereB=(0.00, 1.50, 0.00) |
| P04_constraint_left_of | check | ✅ | ✅ | 2 | check failed=0 passed=4 |
| P05_constraint_on_top | check | ❌ | ✅ | 2 | check failed=0 passed=3 |
| P06_constraint_distance | check | ✅ | ✅ | 2 | check failed=0 passed=1 |
| P07_constraint_facing | check | ❌ | ✅ | 1 | check failed=0 passed=1 |
| P08_constraint_no_overlap | check | ✅ | ✅ | 2 | check failed=0 passed=1 |

CSV: `results_llm_20261020-101745.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_llm_20261020-100417/manifest.ndjson`

## Notes

- **Harness success**: DeepSeek returned a valid plan and Unity CLI steps reported success (or check path completed).
- **Semantic pass (edit)**: post-edit scene query matched prompt criteria before fixture restore.
- **Check pass (constraint)**: `ConstraintChecker` report `success=true` after LLM edits (seeded F03 may already satisfy).
- Fixtures F02/F03 were restored after each prompt in the batch script.
