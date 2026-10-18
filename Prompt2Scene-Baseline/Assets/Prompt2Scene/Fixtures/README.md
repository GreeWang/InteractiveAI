# Prompt2Scene Fixtures

Fixed scenes for formative A/B study (official Unity CLI baseline only).

| ID | Scene | Purpose |
|----|-------|---------|
| F01 | `F01_EmptyRoom.unity` | Generate-from-scratch: empty scene + Main Camera / Directional Light. |
| F02 | `F02_EditBaseline.unity` | Edit-existing: Floor (plane), CubeA, SphereB with fixed transforms. |
| F03 | `F03_ConstraintSandbox.unity` | Constraint sandbox: seeded `RedBox` @ (-1.5,0.5,0), `BlueBall` @ (1.5,0.5,0) for Prompt2Scene-Check sample. |

## Paths
- Project-relative: `Assets/Prompt2Scene/Fixtures/`
- Absolute: `/Users/greenwong/Projects/Prompt2Scene-Baseline/Assets/Prompt2Scene/Fixtures/`

## Rules
- Do not rename fixture IDs mid-study.
- After a run, restore from git or re-open the fixture scene; do not commit polluted fixture state.
- Prompts & run logs live under `~/Projects/Prompt2Scene/eval/` (sibling repo notes), not under Assets.

## Seed state (F02)
- `/Floor` plane @ (0,0,0) scale (2,1,2)
- `/CubeA` cube @ (0,0.5,0)
- `/SphereB` sphere @ (1.5,0.5,0)

## Seed state (F03)
- `/RedBox` cube @ (-1.5, 0.5, 0), rotation yaw 90° (faces BlueBall / +X)
- `/BlueBall` sphere @ (1.5, 0.5, 0)
- `/CupOnBox` sphere @ (-1.5, 1.25, 0) scale 0.4
- Sample constraints: `Assets/Prompt2Scene/Check/Constraints/F03_sample.json` (schema v0.2)
