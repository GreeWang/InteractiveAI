# Prompt2Scene-Check (skeleton)

Constraint validation for formative A/B (`condition=check`) — official Unity CLI baseline only.

## Layout

| Item | Path |
|------|------|
| JSON Schema | `schema/constraint_schema_v0.2.json` (v0.1 kept) |
| Sample (F03) | `constraints/F03_sample.json` |
| In-project JSON | `Prompt2Scene-Baseline/Assets/Prompt2Scene/Check/Constraints/F03_sample.json` |
| Editor C# | `Prompt2Scene-Baseline/Assets/Prompt2Scene/Editor/Prompt2SceneCheck/` |
| Last report | `Prompt2Scene-Baseline/Logs/prompt2scene-check-last.json` |

## Constraint types

### v0.1
- `must_exist` — GameObject by name
- `left_of` — `a.x < b.x`
- `same_y` — `|a.y - b.y| <= epsilon`
- `bounds` — position inside AABB (`min`/`max`)
- `no_overlap` — Colliders + `Physics.ComputePenetration`

### v0.2
- `on_top_of` — `a` above `b`: dy in `[min_vertical, max_vertical]`, XZ offset `<= max_horizontal`
- `distance` — world distance in `[min_distance, max_distance]` (`-1` = open bound)
- `facing` — `target` forward vs `toward` object or `axis`; `max_angle_deg`; `ignore_y` (XZ yaw)

## F03 seed (for sample)
- `RedBox` cube @ (-1.5, 0.5, 0), yaw 90° (faces +X / BlueBall)
- `BlueBall` sphere @ (1.5, 0.5, 0)
- `CupOnBox` sphere @ (-1.5, 1.25, 0) scale 0.4 (on top of RedBox)

## Run

**Editor:** open F03 → **Prompt2Scene → Check → Run Sample F03 Constraints**

**Smoke:**
```bash
export PATH="$HOME/.unity/bin:$PATH"
~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh P04_constraint_left_of check
```

Verified 2026-10-18: F03 sample **10/10 PASS** (incl. on_top_of, distance, facing).

## Schema v0.3

- File: `schema/constraint_schema_v0.3.json`
- New types: `clearance_volume`, `locked_transform`
- Repairer: `ConstraintRepairer.RepairFromPath` (CLI `eval`)
- Snapshots: `SceneSnapshotUtil.SnapshotPosesTo`
- Skill: `skill/SKILL.md`

