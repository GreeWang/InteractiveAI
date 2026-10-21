#!/usr/bin/env bash
# Prompt2Scene LLM harness — OpenAI-compatible plan → optional Unity CLI execute.
# Usage:
#   ./llm_run.sh P02_edit_move_sphere baseline
#   ./llm_run.sh P02_edit_move_sphere baseline --dry-run
#   ./llm_run.sh P04_constraint_left_of check
#   ./llm_run.sh P02_edit_move_sphere check --max-rounds 3
# Env: DEEPSEEK_* (default) or LLM_PROVIDER=bailian + DASHSCOPE_* / LLM_*;
#      see eval/.env.example. Also PROMPT2SCENE_PROJECT, DRY_RUN=1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai

PROMPT_ID=""
CONDITION="baseline"
DRY_RUN=0
MAX_ROUNDS="${LLM_MAX_ROUNDS:-3}"
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --max-rounds)
      MAX_ROUNDS="$2"; shift 2 ;;
    baseline|check)
      if [[ -z "$PROMPT_ID" ]]; then
        CONDITION="$1"; PROMPT_ID="P02_edit_move_sphere"
        [[ "$CONDITION" == "check" ]] && PROMPT_ID="P04_constraint_left_of"
      else
        CONDITION="$1"
      fi
      shift
      ;;
    -*)
      echo "unknown flag: $1" >&2; exit 2
      ;;
    *)
      if [[ -z "$PROMPT_ID" ]]; then PROMPT_ID="$1"
      else CONDITION="$1"
      fi
      shift
      ;;
  esac
done
PROMPT_ID="${PROMPT_ID:-P02_edit_move_sphere}"
CONDITION="${CONDITION:-baseline}"
[[ "${DRY_RUN_ENV:-0}" == "1" ]] && DRY_RUN=1

PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
PROMPTS_FILE="$ROOT/prompts/prompts.json"
RUNS_DIR="$ROOT/runs"
ENV_FILE="$ROOT/.env"

die() { echo "error: $*" >&2; exit 1; }

# Load .env without printing secrets
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Accept DeepSeek, Bailian/DashScope, or generic LLM_* key
if [[ -z "${DEEPSEEK_API_KEY:-}${DASHSCOPE_API_KEY:-}${LLM_API_KEY:-}" ]]; then
  die "no API key set (DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, or LLM_API_KEY in eval/.env)"
fi
[[ -f "$PROMPTS_FILE" ]] || die "prompts missing: $PROMPTS_FILE"
[[ "$CONDITION" == "baseline" || "$CONDITION" == "check" ]] || die "condition must be baseline|check"

iso_now() {
  python3 -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"))'
}

TS="$(date +%Y%m%d-%H%M%S)"
START_ISO="$(iso_now)"
RUN_DIR="$RUNS_DIR/${TS}_${PROMPT_ID}_${CONDITION}_llm"
export RUN_DIR
mkdir -p "$RUN_DIR"
: >"$RUN_DIR/commands.ndjson"
: >"$RUN_DIR/stdout.log"
: >"$RUN_DIR/stderr.log"

PROMPT_JSON="$(PROMPT_ID="$PROMPT_ID" PROMPTS_FILE="$PROMPTS_FILE" python3 -c '
import json, os, sys
pid = os.environ["PROMPT_ID"]
data = json.load(open(os.environ["PROMPTS_FILE"]))
for p in data["prompts"]:
    if p["id"] == pid:
        print(json.dumps(p, ensure_ascii=False))
        sys.exit(0)
sys.stderr.write("prompt not found: %s\n" % pid)
sys.exit(2)
')"

read_field() { P="$PROMPT_JSON" python3 -c "import json,os; print(json.loads(os.environ['P']).get('$1','') or '')"; }
SCENE="$(read_field scene)"
FIXTURE="$(read_field fixture)"
PHASE="$(read_field phase)"
CONSTRAINT_FILE="$(read_field constraint_file)"
TEXT_ZH="$(read_field text_zh)"
TEXT_EN="$(read_field text_en)"
TASK_TEXT="$TEXT_ZH"
[[ -n "$TEXT_EN" ]] && TASK_TEXT="${TEXT_ZH}
${TEXT_EN}"
LLM_HINT="$(read_field llm_hint)"
EXTRA_CTX=""
if [[ -n "$LLM_HINT" ]]; then
  EXTRA_CTX="Layout / placement hint:
${LLM_HINT}"
fi
LLM_SEED="${LLM_SEED:--1}"

OVERALL_OK=1
STEP_ERRORS=()
STATUS_NOTE="ok"
CLI_VERSION=""
if command -v unity >/dev/null 2>&1; then
  CLI_VERSION="$(unity --version 2>/dev/null | head -1 | tr -d '\r' || true)"
fi

# Resolve provider/model/base without printing secrets
LLM_CFG_JSON="$(SCRIPT_DIR="$SCRIPT_DIR" python3 -c '
import json, os, sys
sys.path.insert(0, os.environ["SCRIPT_DIR"])
import llm_client as lc
cfg = lc.resolve_config()
print(json.dumps({
  "provider": cfg["provider"],
  "model": cfg["model"],
  "base_url": cfg["base_url"],
  "completions_url": lc.completions_url(cfg["base_url"]),
}))
')"
export LLM_RESOLVED_MODEL="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["model"])')"
export LLM_RESOLVED_BASE="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["base_url"])')"
export LLM_RESOLVED_PROVIDER="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["provider"])')"

echo "[llm_run] prompt=$PROMPT_ID condition=$CONDITION dry_run=$DRY_RUN"
echo "[llm_run] scene=$SCENE fixture=$FIXTURE"
echo "[llm_run] run_dir=$RUN_DIR"
echo "[llm_run] provider=$LLM_RESOLVED_PROVIDER model=$LLM_RESOLVED_MODEL"
echo "[llm_run] base_url=$LLM_RESOLVED_BASE"
echo "[llm_run] seed=$LLM_SEED"

# --- LLM plan / multi-turn check ---
echo "[llm_run] max_rounds=$MAX_ROUNDS"
PROMPT_JSON_FILE="$RUN_DIR/prompt.json"
printf '%s\n' "$PROMPT_JSON" >"$PROMPT_JSON_FILE"

MULTITURN_USED=0
PLAN_OK=0

if [[ "$CONDITION" == "check" ]]; then
  MULTITURN_USED=1
  set +e
  MT_ARGS=(
    --dotenv "$ENV_FILE"
    --prompt-json "$PROMPT_JSON_FILE"
    --project "$PROJ"
    --run-dir "$RUN_DIR"
    --max-rounds "$MAX_ROUNDS"
  )
  if [[ "$LLM_SEED" != "-1" && -n "$LLM_SEED" ]]; then
    MT_ARGS+=(--seed "$LLM_SEED")
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    MT_ARGS+=(--dry-run)
  fi
  python3 "$SCRIPT_DIR/llm_multiturn.py" "${MT_ARGS[@]}" \
    >"$RUN_DIR/multiturn_stdout.json" 2>"$RUN_DIR/multiturn_stderr.txt"
  MT_RC=$?
  set -e
  if [[ -f "$RUN_DIR/multiturn_summary.json" ]]; then
    FINAL_PASS="$(python3 -c 'import json,sys; print("1" if json.load(open(sys.argv[1])).get("final_pass") else "0")' "$RUN_DIR/multiturn_summary.json")"
    ROUNDS_USED="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("rounds_used",0))' "$RUN_DIR/multiturn_summary.json")"
  else
    FINAL_PASS=0; ROUNDS_USED=0
  fi
  if [[ "$FINAL_PASS" == "1" ]]; then
    PLAN_OK=1
    STATUS_NOTE="multiturn_pass_rounds=${ROUNDS_USED}"
    echo "[llm_run] multiturn PASS rounds=$ROUNDS_USED"
  else
    OVERALL_OK=0
    PLAN_OK=0
    STEP_ERRORS+=("multiturn_failed:rc=${MT_RC}:rounds=${ROUNDS_USED}")
    STATUS_NOTE="multiturn_fail_rounds=${ROUNDS_USED}"
    echo "[llm_run] multiturn FAIL rounds=$ROUNDS_USED rc=$MT_RC" >&2
  fi
  # Copy last llm response to top-level for convenience
  if [[ -f "$RUN_DIR/round_01/llm_response.json" ]]; then
    cp "$RUN_DIR/round_01/llm_response.json" "$RUN_DIR/llm_response.json" 2>/dev/null || true
  fi
else
  # baseline: single-shot (original behavior)
  set +e
  LLM_CLIENT_ARGS=(
    --dotenv "$ENV_FILE"
    --plan
    --scene "$SCENE"
    --fixture "$FIXTURE"
    --task "$TASK_TEXT"
    --out "$RUN_DIR/llm_response.json"
  )
  if [[ -n "$EXTRA_CTX" ]]; then
    LLM_CLIENT_ARGS+=(--extra "$EXTRA_CTX")
  fi
  if [[ "$LLM_SEED" != "-1" && -n "$LLM_SEED" ]]; then
    LLM_CLIENT_ARGS+=(--seed "$LLM_SEED")
  fi
  python3 "$SCRIPT_DIR/llm_client.py" \
    "${LLM_CLIENT_ARGS[@]}" \
    >"$RUN_DIR/llm_client.stdout.json" 2>"$RUN_DIR/llm_client.stderr.txt"
  LLM_RC=$?
  set -e

  if [[ ! -f "$RUN_DIR/llm_response.json" ]]; then
    OVERALL_OK=0
    STEP_ERRORS+=("llm_no_response")
    STATUS_NOTE="llm_failed"
  fi

  PLAN_OK="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("1" if d.get("plan_ok") else "0")' "$RUN_DIR/llm_response.json" 2>/dev/null || echo 0)"
  if [[ "$LLM_RC" -ne 0 || "$PLAN_OK" != "1" ]]; then
    OVERALL_OK=0
    STEP_ERRORS+=("llm_plan_failed:rc=${LLM_RC}")
    STATUS_NOTE="llm_plan_failed"
    echo "[llm_run] LLM plan failed rc=$LLM_RC plan_ok=$PLAN_OK" >&2
  else
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); json.dump(d.get("plan",{}), open(sys.argv[2],"w"), indent=2, ensure_ascii=False); print("commands", len(d.get("plan",{}).get("commands",[])))' \
      "$RUN_DIR/llm_response.json" "$RUN_DIR/plan.json"
    python3 -c '
import pathlib, os
for name in ["llm_response.json", "llm_client.stdout.json"]:
  p = pathlib.Path(os.environ["RUN_DIR"]) / name
  if not p.exists():
    continue
  t = p.read_text(encoding="utf-8", errors="replace")
  for name in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "LLM_API_KEY"):
    key = os.environ.get(name, "")
    if key and key in t:
      t = t.replace(key, "<redacted>")
  p.write_text(t, encoding="utf-8")
'
  fi
fi


run_logged() {
  local label="$1"; shift
  local started_ms ended_ms duration_ms exit_code out_file err_file success
  started_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
  out_file="$(mktemp)"; err_file="$(mktemp)"
  set +e
  unity "$@" >"$out_file" 2>"$err_file"
  exit_code=$?
  set -e
  ended_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
  duration_ms=$((ended_ms - started_ms))
  { echo "===== [${label}] unity $* ====="; cat "$out_file"; echo; } >>"$RUN_DIR/stdout.log"
  if [[ -s "$err_file" ]]; then
    { echo "===== [${label}] unity $* ====="; cat "$err_file"; echo; } >>"$RUN_DIR/stderr.log"
  fi
  success=true
  if [[ "$exit_code" -ne 0 ]]; then
    success=false; OVERALL_OK=0; STEP_ERRORS+=("${label}:exit_${exit_code}")
  elif grep -q '"success"[[:space:]]*:[[:space:]]*false' "$out_file" 2>/dev/null; then
    success=false; OVERALL_OK=0; STEP_ERRORS+=("${label}:success_false")
  fi
  COMMAND_ARGV="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' -- "$@")" \
  LABEL="$label" EXIT_CODE="$exit_code" DURATION_MS="$duration_ms" SUCCESS="$success" \
  OUT_FILE="$out_file" python3 -c '
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo
out = open(os.environ["OUT_FILE"], "r", errors="replace").read()
print(json.dumps({
  "ts": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
  "label": os.environ["LABEL"],
  "argv": ["unity"] + json.loads(os.environ["COMMAND_ARGV"]),
  "exit_code": int(os.environ["EXIT_CODE"]),
  "duration_ms": int(os.environ["DURATION_MS"]),
  "success": os.environ["SUCCESS"] == "true",
  "stdout_snip": out[:2000],
}, ensure_ascii=False))
' >>"$RUN_DIR/commands.ndjson"
  rm -f "$out_file" "$err_file"
  echo "[llm_run] ${label}: success=${success} exit=${exit_code} ${duration_ms}ms"
}

execute_plan() {
  [[ -f "$RUN_DIR/plan.json" ]] || return 1
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[llm_run] dry-run: skip Unity execution"
    STATUS_NOTE="dry_run_plan_only"
    python3 -c '
import json, pathlib, os
from datetime import datetime
from zoneinfo import ZoneInfo
plan=json.load(open(os.environ["RUN_DIR"]+"/plan.json"))
for c in plan.get("commands",[]):
  print(json.dumps({
    "ts": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
    "label": c.get("label","dry"),
    "argv": ["unity","command","--project-path","(dry)",c["command"],"--"]+c.get("args",[]),
    "exit_code": 0,
    "duration_ms": 0,
    "success": True,
    "stdout_snip": "dry-run",
    "dry_run": True,
  }, ensure_ascii=False))
' >>"$RUN_DIR/commands.ndjson"
    return 0
  fi

  command -v unity >/dev/null 2>&1 || die "unity CLI not found (needed unless --dry-run)"
  [[ -d "$PROJ" ]] || die "project not found: $PROJ"

  set +e
  unity status --json >"$RUN_DIR/unity_status.json" 2>/dev/null
  ST=$?
  set -e
  if [[ $ST -ne 0 ]] || ! grep -q '"state"[[:space:]]*:[[:space:]]*"ready"' "$RUN_DIR/unity_status.json" 2>/dev/null; then
    OVERALL_OK=0
    STEP_ERRORS+=("unity_pipeline_not_ready")
    STATUS_NOTE="unity_down_plan_saved"
    echo "[llm_run] Unity Pipeline not ready; plan saved, skip execute" >&2
    return 1
  fi

  run_logged "status" status --json
  run_logged "open_scene" command --project-path "$PROJ" --format json open_scene -- --path "$SCENE"

  # Execute each planned command
  set +e
  RUN_DIR="$RUN_DIR" PROJ="$PROJ" python3 <<'PY'
import json, os, subprocess, pathlib, time
from datetime import datetime
from zoneinfo import ZoneInfo

run = pathlib.Path(os.environ["RUN_DIR"])
proj = os.environ["PROJ"]
plan = json.load(open(run / "plan.json"))
ndjson = open(run / "commands.ndjson", "a", encoding="utf-8")
stdout_log = open(run / "stdout.log", "a", encoding="utf-8")
stderr_log = open(run / "stderr.log", "a", encoding="utf-8")
errors = []

for c in plan.get("commands", []):
    name = c["command"]
    # Skip open_scene if we already opened
    if name == "open_scene":
        continue
    label = c.get("label") or name
    argv = ["unity", "command", "--project-path", proj, "--format", "json", name, "--"] + list(c.get("args") or [])
    t0 = time.time()
    p = subprocess.run(argv, capture_output=True, text=True)
    dur = int((time.time() - t0) * 1000)
    out, err = p.stdout or "", p.stderr or ""
    success = p.returncode == 0 and '"success": false' not in out and '"success":false' not in out
    stdout_log.write(f"===== [{label}] {' '.join(argv)} =====\n{out}\n")
    if err:
        stderr_log.write(f"===== [{label}] {' '.join(argv)} =====\n{err}\n")
    rec = {
        "ts": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "label": label,
        "argv": argv,
        "exit_code": p.returncode,
        "duration_ms": dur,
        "success": success,
        "stdout_snip": out[:2000],
    }
    ndjson.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[llm_run] {label}: success={success} exit={p.returncode} {dur}ms")
    if not success:
        errors.append(label)

ndjson.close(); stdout_log.close(); stderr_log.close()
(run / "exec_errors.json").write_text(json.dumps(errors, indent=2) + "\n", encoding="utf-8")
raise SystemExit(1 if errors else 0)
PY
  EXEC_RC=$?
  set -e
  if [[ $EXEC_RC -ne 0 ]]; then
    OVERALL_OK=0
    STEP_ERRORS+=("exec_plan_failed")
  fi

  # Optional constraint check for F03 / check condition
  if [[ "$CONDITION" == "check" && "$FIXTURE" == "F03" ]]; then
    [[ -n "$CONSTRAINT_FILE" ]] || CONSTRAINT_FILE="Assets/Prompt2Scene/Check/Constraints/F03_sample.json"
    abs_path="$PROJ/${CONSTRAINT_FILE}"
    eval_code="var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@\"${abs_path}\"); return \"success=\"+r.success+\" passed=\"+r.passed+\" failed=\"+r.failed+\" skipped=\"+r.skipped+\" set=\"+r.set_id;"
    run_logged "constraint_check" command --project-path "$PROJ" --format json --result-only eval -- --code "$eval_code"
    report_src="$PROJ/Logs/prompt2scene-check-last.json"
    if [[ -f "$report_src" ]]; then
      cp "$report_src" "$RUN_DIR/check_report.json"
      python3 -c '
import pathlib
p=pathlib.Path("'"$RUN_DIR"'/check_report.json"); b=p.read_bytes()
if b.startswith(b"\xef\xbb\xbf"): p.write_bytes(b[3:])
'
    else
      OVERALL_OK=0; STEP_ERRORS+=("check_report_missing")
    fi
  fi
}

export RUN_DIR
if [[ "$MULTITURN_USED" -eq 0 && "$PLAN_OK" == "1" ]]; then
  execute_plan || true
fi
# For multiturn, semantic/constraint success already decided final_pass; align OVERALL_OK
if [[ "$MULTITURN_USED" -eq 1 ]]; then
  if [[ "${FINAL_PASS:-0}" == "1" ]]; then OVERALL_OK=1; else OVERALL_OK=0; fi
fi

export LLM_MAX_ROUNDS_META="$MAX_ROUNDS"
export LLM_MULTITURN_META="$MULTITURN_USED"
# Merge multiturn_summary into result extras if present
if [[ -f "$RUN_DIR/multiturn_summary.json" ]]; then
  cp "$RUN_DIR/multiturn_summary.json" "$RUN_DIR/check_loop.json" 2>/dev/null || true
fi
END_ISO="$(iso_now)"
success_bool=false
[[ "$OVERALL_OK" -eq 1 ]] && success_bool=true
errs_json="$(printf "%s\n" "${STEP_ERRORS[@]:-}" | python3 -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().splitlines() if l]))')"

python3 -c '
import json, sys
from pathlib import Path
meta = {
  "prompt_id": sys.argv[1],
  "condition": sys.argv[2],
  "phase": sys.argv[3],
  "fixture": sys.argv[4],
  "scene": sys.argv[5],
  "project": sys.argv[6],
  "prompt": json.loads(sys.argv[12]),
  "automation": "llm",
  "started_at": sys.argv[7],
  "ended_at": sys.argv[8],
  "timezone": "Asia/Shanghai",
  "cli_version": sys.argv[9],
  "pipeline_port": 7800,
  "dry_run": sys.argv[10] == "1",
  "provider": __import__("os").environ.get("LLM_RESOLVED_PROVIDER", "deepseek"),
  "model": __import__("os").environ.get("LLM_RESOLVED_MODEL") or __import__("os").environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
  "base_url": __import__("os").environ.get("LLM_RESOLVED_BASE") or __import__("os").environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
  "status_note": sys.argv[11],
  "max_rounds": int(__import__("os").environ.get("LLM_MAX_ROUNDS_META") or "3"),
  "multiturn": __import__("os").environ.get("LLM_MULTITURN_META") == "1",
}
Path(sys.argv[13]).write_text(json.dumps(meta, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
' "$PROMPT_ID" "$CONDITION" "$PHASE" "$FIXTURE" "$SCENE" "$PROJ" "$START_ISO" "$END_ISO" "$CLI_VERSION" "$DRY_RUN" "$STATUS_NOTE" "$PROMPT_JSON" "$RUN_DIR/meta.json"

python3 -c '
import json, sys
from pathlib import Path
import os
from pathlib import Path
extra={}
ms=Path(sys.argv[4])/"multiturn_summary.json"
if ms.exists():
  extra=json.load(open(ms))
Path(sys.argv[5]).write_text(json.dumps({
  "success": sys.argv[1]=="true",
  "prompt_id": sys.argv[2],
  "condition": sys.argv[3],
  "run_dir": sys.argv[4],
  "errors": json.loads(sys.argv[6]),
  "summary": sys.argv[7],
  "automation": "llm",
  "provider": os.environ.get("LLM_RESOLVED_PROVIDER", "deepseek"),
  "model": os.environ.get("LLM_RESOLVED_MODEL") or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
  "status_note": sys.argv[8],
  "dry_run": sys.argv[9]=="1",
  "max_rounds": int(os.environ.get("LLM_MAX_ROUNDS_META") or "3"),
  "multiturn": os.environ.get("LLM_MULTITURN_META")=="1",
  "final_pass": extra.get("final_pass"),
  "rounds_used": extra.get("rounds_used"),
}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
' "$success_bool" "$PROMPT_ID" "$CONDITION" "$RUN_DIR" "$RUN_DIR/result.json" "$errs_json" "llm condition=$CONDITION" "$STATUS_NOTE" "$DRY_RUN"

echo "[llm_run] wrote $RUN_DIR"
echo "[llm_run] success=$success_bool note=$STATUS_NOTE"
[[ "$OVERALL_OK" -eq 1 ]]
