# Prompt2Scene-Check Agent Skill

Teach an agent how to run **Prompt2Scene-Check** (ConstraintChecker) against a Unity scene using the **official Unity Pipeline CLI only** (no third-party MCP).

## When to use

- After editing or generating scene objects, verify spatial / existence constraints.
- In a repair loop: run check → read failures → emit a minimal Unity CLI plan → re-check.

## Prerequisites

- Unity Editor has the project open with Pipeline ready: `unity status` → port **7800** `ready`.
- Project path (default): `~/Projects/Prompt2Scene-Baseline` or `$PROMPT2SCENE_PROJECT`.
- Checker scripts live under `Assets/Prompt2Scene/Editor/Prompt2SceneCheck/`.
- Constraint JSON files: repo `check/constraints/*.json` (mirrored into the Unity project at `Assets/Prompt2Scene/Check/Constraints/`).

## Schema

- v0.1 / v0.2: `check/schema/constraint_schema_v0.2.json`
- Types: `must_exist`, `left_of`, `same_y`, `bounds`, `no_overlap`, `on_top_of`, `distance`, `facing`

### `on_top_of` (important)

- Fields: `a` (top), `b` (support), `max_horizontal` (default 0.5), `min_vertical`, `max_vertical`
- Passes when horizontal XZ distance ≤ `max_horizontal` and dy = a.y−b.y in `[min_vertical, max_vertical]`
- **Always match support X/Z.** Do not assume the support is at the world origin.

Example (`check/constraints/P05_on_top.json`): CupOnBox on RedBox; F03 seed RedBox≈`(-1.5,0.5,0)` → CupOnBox≈`[-1.5,1.25,0]`.

## Run a constraint set via CLI

```bash
export PATH="$HOME/.unity/bin:$PATH"
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ABS="$PROJ/Assets/Prompt2Scene/Check/Constraints/P05_on_top.json"

unity command --project-path "$PROJ" open_scene -- \
  --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity

unity command --project-path "$PROJ" --format json --result-only eval -- --code \
  "var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@\"$ABS\"); return \"success=\"+r.success+\" passed=\"+r.passed+\" failed=\"+r.failed;"
```

Report file (UTF-8, may have BOM): `$PROJ/Logs/prompt2scene-check-last.json`

Editor menu alternative: **Prompt2Scene → Check → Run Sample F03 Constraints**.

## Interpret the report

```json
{
  "set_id": "P05_on_top",
  "success": false,
  "passed": 2,
  "failed": 1,
  "results": [
    {"id": "c_on", "type": "on_top_of", "passed": false,
     "message": "XZ offset=1.5 > max_horizontal=0.5"}
  ]
}
```

- Overall pass: `success == true` (and `failed == 0`).
- Use each failed `message` as repair feedback.
- Helper script: `check/apply_and_verify.sh` (if present) wraps open + eval + copy report.

## Repair loop tips

1. Open the target fixture scene; do not leave objects from a prior prompt hanging.
2. Emit a **minimal** Unity CLI plan (`set_transform` / `create_gameobject` / …).
3. Re-run ConstraintChecker; stop when `success=true` or max rounds reached.
4. Prefer known fixture seeds over mid-plan `get_component_properties` in single-shot plans (results are not fed back until the next turn).
5. For `on_top_of` XZ failures: copy support `x,z`; set `y ≈ support.y + 0.75`.
6. Never print or embed API keys in plans or logs.

## Fixtures (quick map)

| Fixture | Role | Seed objects |
|---------|------|--------------|
| F01_EmptyRoom | generate | empty |
| F02_EditBaseline | edit | Floor, CubeA≈(0,0.5,0), SphereB≈(1.5,0.5,0) |
| F03_ConstraintSandbox | constraints | RedBox≈(-1.5,0.5,0), BlueBall≈(1.5,0.5,0), CupOnBox |

## Related repo paths

- Eval prompts: `eval/prompts/prompts.json`
- LLM harness (optional): `eval/scripts/llm_run.sh` condition `check`
- Protocol: `EVAL_PROTOCOL.md`
