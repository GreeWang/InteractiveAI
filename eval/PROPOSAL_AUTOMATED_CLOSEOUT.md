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

## Aggregate metrics (qwen3.8-max, Asia/Shanghai)

| Suite | Cells | baseline | check | notes |
|-------|-------|----------|-------|-------|
| Scripted task matrix (12×3×A/B) | 72 | **36/36 (100%)** | **36/36 (100%)** | `RESULTS_TASK_MATRIX.md` |
| Held-out A/B | 72 | **33/36 (92%)** | **36/36 (100%)** | 12 briefs (shortfall vs proposal **24**); all 3 fails = `H12_preserve_red` baseline; check repaired each in 2 rounds. `RESULTS_HELDOUT_AB.md` |
| Skill-only ablation (6×3 arms) | 18 | **6/6 (100%)** | **6/6 (100%)** | skill arm also **6/6 (100%)**. `RESULTS_ABLATION.md` |
| Checker P/R (single-annotator) | 16 labelled | — | P=R=F1=**1.000** | `CHECKER_PR.md` (not independent second assessor) |

**Shortfall:** proposal called for 24 held-out briefs ×3 ×A/B; this closeout ran **12** held-out briefs (72 cells) for cost/time. Expanding 12→24 remains in Human-remaining / future budget.

CSV mirrors: `results_task_matrix.csv`, `results_heldout_ab.csv`, `results_ablation.csv`.

## Human-remaining

- Developer interviews / think-aloud
- Counterbalanced human A/B + usability scores
- Independent second assessor
- Unity in-editor Assistant walkthrough (account-gated)
- Expanding held-out from 12→24 if budget allows

## Model policy

Held-out A/B and closeout matrices use **one fixed model** (`qwen3.8-max` via Bailian) for condition fairness. Prior formative R1 used DeepSeek V4-Pro as a separate comparative round.
