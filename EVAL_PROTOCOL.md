# Prompt2Scene Formative Eval Protocol / 评测协议（Step 1）

Updated: 2026-10-18 Asia/Shanghai (UTC+8) — 10-prompt formative A/B first pass

## Goal / 目标
Minimal A/B baseline using **official Unity Pipeline CLI only** (no third-party MCP).  
用官方 Unity CLI 跑通「生成 → 编辑 → 落盘日志」，为 Prompt2Scene-Check 做对照。

## Layout / 目录

| Role | Path |
|------|------|
| Unity project | `~/Projects/Prompt2Scene-Baseline` |
| Fixtures (scenes) | `Prompt2Scene-Baseline/Assets/Prompt2Scene/Fixtures/` |
| Prompts | `~/Projects/Prompt2Scene/eval/prompts/prompts.json` |
| Run logs | `~/Projects/Prompt2Scene/eval/runs/` |
| Smoke script | `~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh` |
| Stack notes | `~/Projects/Prompt2Scene/BASELINE_STACK.txt` |

## Fixtures

- **F01_EmptyRoom** — generate from scratch  
- **F02_EditBaseline** — edit existing (Floor / CubeA / SphereB seeded)  
- **F03_ConstraintSandbox** — spatial / constraint checks (empty for now)

See `Assets/Prompt2Scene/Fixtures/README.md`.

## Logging convention / 日志约定

Run dir: `eval/runs/<YYYYMMDD-HHMMSS>_<prompt_id>_<condition>/`

Required files:
- `meta.json` — prompt, fixture, condition, start/end (Asia/Shanghai), CLI version, Editor version  
- `commands.ndjson` — each `unity` invocation (argv, exit_code, duration_ms, success)  
- `stdout.log` / `stderr.log`  
- `result.json` — overall success + short summary  

Condition labels: `baseline` | `check` (Prompt2Scene-Check constraint pass/fail).

## CLI reminders
```bash
export PATH="$HOME/.unity/bin:$PATH"
unity status
unity command --project-path ~/Projects/Prompt2Scene-Baseline open_scene -- --path Assets/Prompt2Scene/Fixtures/F01_EmptyRoom.unity
```

Args after command name need `--` then `--flag value` (e.g. `-- --path Assets/...`).

## Invoke smoke / 冒烟用法

```bash
export PATH="$HOME/.unity/bin:$PATH"
~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh                         # P02 + baseline
~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh P02_edit_move_sphere baseline
~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh P04_constraint_left_of check
~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh check                   # shorthand → P04 + check
```

- **baseline (P02/F02):** status → open → find → move SphereB → restore → save  
- **check (P04/F03):** status → open F03 → `ConstraintChecker.RunDefaultSample()` via `eval` → copy `check_report.json` into run dir  

Example runs:
- `eval/runs/20261017-154222_P02_edit_move_sphere_baseline/`
- `eval/runs/20261017-155714_P04_constraint_left_of_check/`

## Prompt2Scene-Check (`condition=check`)

Skeleton under `~/Projects/Prompt2Scene/check/` + Editor scripts in the Unity project.

| Item | Path |
|------|------|
| Schema | `~/Projects/Prompt2Scene/check/schema/constraint_schema_v0.2.json` |
| Sample | `~/Projects/Prompt2Scene/check/constraints/F03_sample.json` |
| In-project JSON | `Assets/Prompt2Scene/Check/Constraints/F03_sample.json` |
| Editor C# | `Assets/Prompt2Scene/Editor/Prompt2SceneCheck/` |
| Last report | `Prompt2Scene-Baseline/Logs/prompt2scene-check-last.json` |
| README | `~/Projects/Prompt2Scene/check/README.md` |

Types: v0.1 `must_exist`/`left_of`/`same_y`/`bounds`/`no_overlap`; v0.2 `on_top_of`/`distance`/`facing`.

**Editor:** open F03 → menu **Prompt2Scene → Check → Run Sample F03 Constraints**

**CLI:**
```bash
export PATH="$HOME/.unity/bin:$PATH"
unity command --project-path ~/Projects/Prompt2Scene-Baseline open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity
unity command --project-path ~/Projects/Prompt2Scene-Baseline eval -- --code 'var r = Prompt2Scene.Check.ConstraintChecker.RunDefaultSample(); return r.success+" "+r.passed+"/"+ (r.passed+r.failed);'
```

Verified 2026-10-18: F03 sample **10/10 PASS** (incl. on_top_of, distance, facing).

## Formative A/B (first pass)

Prompts: `eval/prompts/prompts.json` (**10** items).  
Batch: `eval/scripts/run_ab_batch.sh` → summary `eval/RESULTS_AB.md` + `eval/results_ab_*.csv`.

| automation | meaning | this pass |
|---|---|---|
| `baseline_cli` | Unity CLI edit smoke (no LLM) | P02, P03, P09 |
| `check_cli` | ConstraintChecker on seeded F03 | P04–P08 |
| `none` | generate / LLM not wired | P01, P10 skipped |

Smoke uses per-prompt `constraint_file` / `baseline_action`. True LLM A/B generation not implemented yet.

## Next steps
1. ~~Fixtures + logging~~  
2. ~~`smoke_run.sh` end-to-end~~  
3. ~~Prompt2Scene-Check schema + Editor checker on F03~~  
4. ~~Wire `condition=check` into smoke~~ — next: richer constraints / A/B batch runner  

## Restore fixtures
After a dirty run: discard scene changes in Editor, or re-checkout fixture `.unity` files from git once versioned.

## LLM harness (DeepSeek) / 真 LLM 生成

Scripts (under `eval/scripts/`):
- `llm_client.py` — OpenAI-compatible DeepSeek chat; `--plan` asks for a JSON Unity CLI command list
- `llm_run.sh` — load prompt → call DeepSeek → (optional) execute via `unity command` → optional Check on F03

### Config (do not commit secrets)

```bash
# eval/.env  (gitignored)  or export in shell / ~/.zshrc
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com   # default
DEEPSEEK_MODEL=deepseek-v4-pro                 # default
```

Template: `eval/.env.example`.

### Invoke

```bash
export PATH="$HOME/.unity/bin:$PATH"
cd ~/Projects/InteractiveAI

# Plan only (no Unity execute)
./eval/scripts/llm_run.sh P02_edit_move_sphere baseline --dry-run

# Plan + execute on live Pipeline (port 7800)
./eval/scripts/llm_run.sh P02_edit_move_sphere baseline

# After edits, also run ConstraintChecker when fixture is F03
./eval/scripts/llm_run.sh P04_constraint_left_of check
```

Dry-run still calls the API and writes `plan.json` under `eval/runs/<ts>_<id>_<condition>_llm/`.
Logs: `llm_response.json`, `plan.json`, `commands.ndjson`, `meta.json`, `result.json`.

Allowed plan commands: `open_scene`, `save_scene`, `find_gameobjects`, `create_gameobject`, `delete_gameobject`, `set_transform`, `get_component_properties`, `eval`.

### Multi-turn repair (`condition=check`)

`llm_run.sh … check` uses `llm_multiturn.py`:
plan → execute → verify → on failure, feed report back to the model (default **3** rounds).

```bash
./eval/scripts/llm_run.sh P02_edit_move_sphere check --max-rounds 3
./eval/scripts/llm_run.sh P04_constraint_left_of check
# or: LLM_MAX_ROUNDS=3 ./eval/scripts/llm_run.sh P03_edit_duplicate_row check
```

- **F03**: verify = ConstraintChecker JSON
- **Edit prompts (P02/P03/P09)**: verify = semantic postcheck from `success_criteria` (above / spacing 1.2–1.8 / y≈2)
- Per-round logs: `eval/runs/<run>/round_01/…`, summary `multiturn_summary.json`

