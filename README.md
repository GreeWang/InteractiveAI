# InteractiveAI / Prompt2Scene

Formative-study stack for prompt-driven Unity scene editing with constraint checking (Prompt2Scene-Check).

## Layout

| Path | Contents |
|------|----------|
| `eval/` | Prompts, smoke scripts, A/B run logs, results |
| `check/` | Constraint schemas + apply/verify helpers |
| `Prompt2Scene-Baseline/` | Unity 6 URP project (fixtures + Check Editor scripts) |
| `vendor/` | Offline `com.unity.pipeline` tarball (optional) |
| `EVAL_PROTOCOL.md` | Eval protocol |
| `BASELINE_STACK.txt` | Tooling baseline notes |

## Requirements

- Unity 6000.x (URP) with project at `Prompt2Scene-Baseline/`
- Embedded package: `Packages/com.unity.pipeline` (`file:com.unity.pipeline`)
- Official Unity MCP / Pipeline HTTP (default port **7800**)

## Quick eval

```bash
# from repo root
./eval/scripts/smoke_run.sh P02_edit_move_sphere baseline
./eval/scripts/smoke_run.sh P04_constraint_left_of check
```

Editor menu: **Prompt2Scene → Check → Run Sample F03**

## Git notes

Unity `Library/`, `Temp/`, `Logs/`, `UserSettings/`, and generated `*.csproj` / `*.sln` are ignored. Open the project in Unity once after clone to regenerate them.
