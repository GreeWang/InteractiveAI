# Formal Formative — r3_gen_qwen

Updated: 2026-10-21T15:34:39+08:00 Asia/Shanghai (UTC+8)
Batch: `batch_formal_r3_gen_qwen_20261021-153324`
Provider/Model: **bailian / qwen3.8-max** · seeds=**[1]** · check max_rounds=**3**

## Aggregate success (semantic / ConstraintChecker)

- **generate**: baseline 2/2 (100%) · check 2/2 (100%)
- **all**: baseline 2/2 (100%) · check 2/2 (100%)

## Per-seed

- seed=1: baseline 2/2 (100%) · check 2/2 (100%)

## Matrix

| seed | prompt | condition | harness_ok | semantic/check_ok | rounds | notes |
|---|---|---|---|---|---|---|
| 1 | P01_generate_table | baseline | ✅ | ✅ | 1 | `pass=True;exists=True;horiz=0;dy=0.75;Table=(0.00, 0.50, 0.00);Cup=(0.00, 1.25, ` |
| 1 | P01_generate_table | check | ✅ | ✅ | 1 | `pass=True;exists=True;horiz=0;dy=0.75;Table=(0.00, 0.50, 0.00);Cup=(0.00, 1.25, ` |
| 1 | P10_generate_row | baseline | ✅ | ✅ | 1 | `pass=True;exists=True;dAB=1;dBC=1;A=(0.00, 0.50, 0.00);B=(1.00, 0.50, 0.00);C=(2` |
| 1 | P10_generate_row | check | ✅ | ✅ | 1 | `pass=True;exists=True;dAB=1;dBC=1;detail=ABC_spacing` |

CSV: `results_formal_r3_gen_qwen_20261021-153439.csv`
Manifest: `/Users/greenwong/Projects/InteractiveAI/eval/runs/batch_formal_r3_gen_qwen_20261021-153324/manifest.ndjson`

