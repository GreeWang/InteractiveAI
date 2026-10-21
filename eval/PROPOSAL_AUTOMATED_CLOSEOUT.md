# Proposal automated closeout

Updated: 2026-10-21 Asia/Shanghai (UTC+8)

Maps the 15 Oct 2026 course proposal to **agent-completable** work. Human-subject studies are explicitly out of scope.

## Completed (this closeout)

| # | Item | Artifact |
|---|------|----------|
| 1 | Week-2 decision gate (agent evidence) | `eval/WEEK2_DECISION_GATE.md` |
| 2 | Check MVP → v0.3 (clearance, locked, repair, snapshots) | `check/schema/constraint_schema_v0.3.json`, Editor scripts, `check/skill/SKILL.md` |
| 3 | ~20 object catalog | `eval/object_catalog.json` |
| 4 | Scripted task matrix ≈12×3 | `eval/RESULTS_TASK_MATRIX.md` |
| 5 | Held-out A/B (12 briefs ×3 seeds; shortfall vs proposal 24 noted) | `eval/RESULTS_HELDOUT_AB.md` |
| 6 | Checker precision/recall (single-annotator) | `eval/CHECKER_PR.md` |
| 7 | Skill-only ablation (6 briefs × 3 arms) | `eval/RESULTS_ABLATION.md` |
| 8 | Docs + push | this file, `EVAL_PROTOCOL.md`, `README.md` |

## Metrics placeholder

Filled after batch jobs finish (task matrix → held-out → ablation).

## Human-remaining

- Developer interviews / think-aloud
- Counterbalanced human A/B + usability scores
- Independent second assessor
- Unity in-editor Assistant walkthrough (account-gated)
- Expanding held-out from 12→24 if budget allows

## Model policy

Held-out A/B and closeout matrices use **one fixed model** (`qwen3.8-max` via Bailian) for condition fairness. Prior formative R1 used DeepSeek V4-Pro as a separate comparative round.
