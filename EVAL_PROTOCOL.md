# Prompt2Scene Formative Eval Protocol / 评测协议

Updated: 2026-10-21 Asia/Shanghai (UTC+8)

## Goal / 目标

Minimal formative A/B using **official Unity Pipeline CLI only** (no third-party MCP).  
LLM emits a Unity CLI JSON plan → harness executes → semantic / ConstraintChecker score.  
Conditions: **baseline** (single-shot) vs **check** (multiturn repair ≤3 rounds).

## Layout / 目录

| Role | Path |
|------|------|
| Repo | `~/Projects/InteractiveAI` |
| Unity project | `~/Projects/Prompt2Scene-Baseline` (or `$PROMPT2SCENE_PROJECT`) |
| Fixtures | `Assets/Prompt2Scene/Fixtures/` |
| Prompts | `eval/prompts/prompts.json` (v0.3) |
| Run logs | `eval/runs/` |
| LLM harness | `eval/scripts/llm_run.sh` |
| Formal batch | `eval/scripts/run_formal_batch.sh` |
| Check schema / samples | `check/schema/`, `check/constraints/` |
| Check agent skill | `check/skill/SKILL.md` |
| Findings | `eval/FORMATIVE_FINDINGS.md` |

## Fixtures

| Id | Scene | Role | Seeds |
|----|-------|------|-------|
| F01 | `F01_EmptyRoom` | generate | empty (cleared between cells) |
| F02 | `F02_EditBaseline` | edit | CubeA≈(0,0.5,0), SphereB≈(1.5,0.5,0) |
| F03 | `F03_ConstraintSandbox` | constraints | RedBox≈(-1.5,0.5,0), BlueBall≈(1.5,0.5,0), CupOnBox near RedBox |

**P05 prep:** before each `P05_constraint_on_top` cell, CupOnBox is moved to `[0,0.5,0]` so `on_top_of` is a real placement task (seed often already satisfies the constraint).

## Prompt matrix

| Id | Phase | Fixture | Notes |
|----|-------|---------|-------|
| P01 | generate | F01 | Table + Cup on table |
| P02/P03/P09 | edit | F02 | move / duplicate / raise |
| P04–P08 | constraint | F03 | left_of / on_top / distance / facing / no_overlap |
| P10 | generate | F01 | cubes A B C ~1m apart |

## LLM providers

OpenAI-compatible chat completions via `eval/scripts/llm_client.py`.

| Provider | Env | Default model |
|----------|-----|---------------|
| DeepSeek (default) | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | `deepseek-v4-pro` |
| Bailian / DashScope | `LLM_PROVIDER=bailian`, `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, `DASHSCOPE_MODEL` | `qwen3.8-max` |

Copy `eval/.env.example` → `eval/.env` (gitignored). Never commit keys.  
Caller exports (e.g. `LLM_PROVIDER`) are preserved when scripts re-source `.env`.  
Optional: `LLM_SEED` / `--seed` for API seed; `LLM_MAX_ROUNDS` for check.

```bash
export PATH="$HOME/.unity/bin:$PATH"
# DeepSeek
./eval/scripts/llm_run.sh P02_edit_move_sphere baseline
# Bailian
export LLM_PROVIDER=bailian
./eval/scripts/llm_run.sh P05_constraint_on_top check
```

## Formal rounds

| Round | Script / tag | Model | Cells |
|-------|--------------|-------|-------|
| R1 | `run_formal_r1.sh` | deepseek-v4-pro | P02–P09 × baseline/check · seed 1 |
| R2 | `run_formal_r2.sh` + `run_formal_r2_retry.sh` | qwen3.8-max | same; dirty cells retried |
| R3 generate | `run_formal_r3_generate.sh ds\|qwen` | both | P01/P10 × baseline/check · seed 1 |
| Multiseed | `run_formal_multiseed.sh ds\|qwen 2,3` | both | P02–P09 seeds 2–3; aggregate with R1/R2 seed 1 |

Generic driver: `FORMAL_TAG=… FORMAL_PROMPTS=… FORMAL_SEEDS=1,2,3 ./eval/scripts/run_formal_batch.sh`  
Writers: `write_formal_r1_results.py`, `write_formal_r2_results.py`, `write_formal_batch_results.py`, `patch_r2_with_retry.py`.

Results: `eval/RESULTS_FORMAL_R1.md`, `RESULTS_FORMAL_R2.md`, `RESULTS_FORMAL_R3_GEN_*.md`, `RESULTS_FORMAL_MULTISEED.md`.

## Logging convention

Run dir: `eval/runs/<YYYYMMDD-HHMMSS>_<prompt_id>_<condition>_llm/`

- `meta.json`, `commands.ndjson`, `stdout.log` / `stderr.log`, `result.json`
- baseline: `plan.json`, `llm_response.json`, optional `check_report.json` / `r1_postcheck.json`
- check: `multiturn_summary.json`, `round_XX/`

Timestamps: **Asia/Shanghai (UTC+8)**.

## Prompt2Scene-Check

| Item | Path |
|------|------|
| Schema | `check/schema/constraint_schema_v0.2.json` |
| Samples | `check/constraints/*.json` |
| Editor C# | `Assets/Prompt2Scene/Editor/Prompt2SceneCheck/` |
| Last report | `$PROJ/Logs/prompt2scene-check-last.json` |
| Agent skill | `check/skill/SKILL.md` |

Types: v0.1 `must_exist` / `left_of` / `same_y` / `bounds` / `no_overlap`; v0.2 `on_top_of` / `distance` / `facing`.

`on_top_of`: match support X/Z (`max_horizontal` default 0.5); dy in `[min_vertical, max_vertical]`. **Do not loosen thresholds without documenting before/after.**

## CLI reminders

```bash
export PATH="$HOME/.unity/bin:$PATH"
unity status   # expect ready on :7800
unity command --project-path ~/Projects/Prompt2Scene-Baseline open_scene -- \
  --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity
```

Args after the command name need `--` then flags.

## Smoke

```bash
./eval/scripts/smoke_run.sh P02_edit_move_sphere baseline   # CLI-only edit smoke
./eval/scripts/smoke_run.sh P04_constraint_left_of check
./eval/scripts/llm_run.sh P01_generate_table baseline         # LLM generate
```

---

## Closeout addendum (2026-10-21 Asia/Shanghai)

Automated proposal closeout (no human subjects):

- **Check schema v0.3**: `clearance_volume`, `locked_transform`; enriched reports; `ConstraintRepairer`; scene pose snapshots.
- **Catalog (~20)**: `eval/object_catalog.json` / `Assets/Prompt2Scene/Catalog/object_catalog.json`.
- **Prompts P01–P12** + held-out `eval/prompts/heldout.json` (H01–H12).
- **Week-2 gate (agent)**: `eval/WEEK2_DECISION_GATE.md`.
- **Batches**: `eval/scripts/run_closeout_batch.sh` (task matrix / held-out A/B / ablation).
- **Default model for large closeout batches**: Bailian `qwen3.8-max` (fixed across A/B). DeepSeek reserved for comparative cells.
- **Human-only leftovers**: interviews, counterbalanced ratings, second assessor, in-editor Assistant (see gate doc).

