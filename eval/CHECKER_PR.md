# Checker Precision / Recall

Updated: 2026-10-21T16:08:56+0800 Asia/Shanghai

**Annotator:** single-agent (labeller = same agent that designed fixtures). **Not** an independent second human assessor.

## Setup

- 8 labelled **valid** + 8 **invalid** F03 configurations
- Constraint files: P04–P08, P11–P12, F03_sample
- Labels + pose snapshots: `eval/fixtures_labelled/`

## Confusion

| | Pred valid | Pred invalid |
|--|--|--|
| Label valid | 8 | 0 |
| Label invalid | 0 | 8 |

- Precision = 1.000
- Recall = 1.000
- F1 = 1.000
- Accuracy = 1.000 (16/16)

## Per-case

| id | label | predicted | match |
|----|-------|-----------|-------|
| V01_left_ok | valid | valid | ✅ |
| V02_on_top_ok | valid | valid | ✅ |
| V03_dist_ok | valid | valid | ✅ |
| V04_face_ok | valid | valid | ✅ |
| V05_no_overlap_ok | valid | valid | ✅ |
| V06_clear_ok | valid | valid | ✅ |
| V07_locked_ok | valid | valid | ✅ |
| V08_f03_sample_ok | valid | valid | ✅ |
| I01_left_fail | invalid | invalid | ✅ |
| I02_on_top_xz_fail | invalid | invalid | ✅ |
| I03_dist_fail | invalid | invalid | ✅ |
| I04_face_fail | invalid | invalid | ✅ |
| I05_overlap_fail | invalid | invalid | ✅ |
| I06_clear_fail | invalid | invalid | ✅ |
| I07_locked_fail | invalid | invalid | ✅ |
| I08_missing_fail | invalid | invalid | ✅ |

## Caveat

Single-annotator gold labels; precision/recall here measure checker agreement with agent-authored fixtures, not inter-rater reliability.
