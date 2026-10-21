# Prompt2Scene-Check Agent Skill

Teach an agent how to run **Prompt2Scene-Check** (ConstraintChecker) against a Unity scene using the **official Unity Pipeline CLI only** (no third-party MCP).

## When to use

- After editing or generating scene objects, verify spatial / existence constraints.
- In a repair loop: run check → read failures → emit a minimal Unity CLI plan → re-check.
- Optional **deterministic repair**: `ConstraintRepairer.RepairFromPath` for clearance / no_overlap / on_top / left_of / same_y (never moves `locked` / `locked_transform` targets).

## Prerequisites

- Unity Editor has the project open with Pipeline ready: `unity status` → port **7800** `ready`.
- Project path (default): `~/Projects/Prompt2Scene-Baseline` or `$PROMPT2SCENE_PROJECT`.
- Checker scripts: `Assets/Prompt2Scene/Editor/Prompt2SceneCheck/`.
- Constraint JSON: repo `check/constraints/*.json` (mirrored at `Assets/Prompt2Scene/Check/Constraints/`).
- Object catalog (~20): `Assets/Prompt2Scene/Catalog/object_catalog.json` / `eval/object_catalog.json`.

## Schema

- **v0.3**: `check/schema/constraint_schema_v0.3.json` (preferred)
- v0.2 still valid for older types
- Types: `must_exist`, `left_of`, `same_y`, `bounds`, `no_overlap`, `on_top_of`, `distance`, `facing`, **`clearance_volume`**, **`locked_transform`**
- Optional set-level `locked: string[]` — repairer must not move these names

### `clearance_volume`

- Keep-out AABB `min`/`max` (+ optional `padding`)
- `objects[]` and/or `target`/`a`/`b` must stay **outside** (AABB or transform point)
- Calls `Physics.SyncTransforms()` before measuring

### `locked_transform`

- `target` + `position` / optional `rotation_euler`
- `check_position` / `check_rotation`, `pos_epsilon`, `rot_epsilon_deg`

### Report enrichment (v0.3)

Each result may include `object_a`, `object_b`, `measurement`, `expected` besides `message`.

### `on_top_of`

- Match support X/Z; `y ≈ support.y + 0.75`. Never assume support is at origin.

## Run via CLI

```bash
export PATH="$HOME/.unity/bin:$PATH"
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ABS="$PROJ/Assets/Prompt2Scene/Check/Constraints/P11_clearance.json"

unity command --project-path "$PROJ" open_scene -- \
  --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity

unity command --project-path "$PROJ" --format json --result-only eval -- --code \
  "var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@\"$ABS\"); return \"success=\"+r.success+\" failed=\"+r.failed;"
```

Report: `$PROJ/Logs/prompt2scene-check-last.json`

### Deterministic repair (≤3 rounds)

```bash
unity command --project-path "$PROJ" --format json --result-only eval -- --code \
  "var rr = Prompt2Scene.Check.ConstraintRepairer.RepairFromPath(@\"$ABS\", 3); return \"ok=\"+rr.success_after+\" rounds=\"+rr.rounds;"
```

Repair log: `$PROJ/Logs/prompt2scene-repair-last.json`

### Scene snapshot (poses JSON)

```bash
unity command --project-path "$PROJ" --format json --result-only eval -- --code \
  "return Prompt2Scene.Check.SceneSnapshotUtil.SnapshotPosesTo(@\"/tmp/scene_poses.json\");"
```

## Repair loop tips

1. Restore fixture; snapshot before edits when logging.
2. Minimal CLI plan; re-check; stop on success or max rounds.
3. Prefer catalog / fixture seed coords over mid-plan property reads in single-shot plans.
4. Never print API keys.

## Fixtures

| Fixture | Role | Seeds |
|---------|------|-------|
| F01_EmptyRoom | generate | empty |
| F02_EditBaseline | edit | Floor, CubeA≈(0,0.5,0), SphereB≈(1.5,0.5,0) |
| F03_ConstraintSandbox | constraints | RedBox≈(-1.5,0.5,0), BlueBall≈(1.5,0.5,0), CupOnBox |

## Related

- Prompts: `eval/prompts/prompts.json` (P01–P12)
- Protocol: `EVAL_PROTOCOL.md`
- Week-2 gate: `eval/WEEK2_DECISION_GATE.md`
