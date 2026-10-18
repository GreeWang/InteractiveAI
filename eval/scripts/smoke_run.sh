#!/usr/bin/env bash
# Prompt2Scene formative smoke — official Unity CLI only.
# Usage: ./smoke_run.sh [prompt_id] [condition]   OR   ./smoke_run.sh check|baseline [prompt_id]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${1:-}" == "check" || "${1:-}" == "baseline" ]]; then
  CONDITION="$1"
  if [[ "$CONDITION" == "check" ]]; then
    PROMPT_ID="${2:-P04_constraint_left_of}"
  else
    PROMPT_ID="${2:-P02_edit_move_sphere}"
  fi
else
  PROMPT_ID="${1:-P02_edit_move_sphere}"
  CONDITION="${2:-baseline}"
fi

export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
PROMPTS_FILE="$ROOT/prompts/prompts.json"
RUNS_DIR="$ROOT/runs"

die() { echo "error: $*" >&2; exit 1; }
command -v unity >/dev/null 2>&1 || die "unity CLI not found"
[[ -d "$PROJ" ]] || die "project not found: $PROJ"
[[ -f "$PROMPTS_FILE" ]] || die "prompts missing"
[[ "$CONDITION" == "baseline" || "$CONDITION" == "check" ]] || die "bad condition"

iso_now() {
  python3 -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"))'
}

TS="$(date +%Y%m%d-%H%M%S)"
START_ISO="$(iso_now)"
RUN_DIR="$RUNS_DIR/${TS}_${PROMPT_ID}_${CONDITION}"
mkdir -p "$RUN_DIR"
: >"$RUN_DIR/commands.ndjson"
: >"$RUN_DIR/stdout.log"
: >"$RUN_DIR/stderr.log"

CLI_VERSION="$(unity --version 2>/dev/null | head -1 | tr -d '\r' || true)"

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
AUTOMATION="$(read_field automation)"
BASELINE_ACTION="$(read_field baseline_action)"
CONSTRAINT_FILE="$(read_field constraint_file)"
[[ -n "$CONSTRAINT_FILE" ]] || CONSTRAINT_FILE="Assets/Prompt2Scene/Check/Constraints/F03_sample.json"

OVERALL_OK=1
STEP_ERRORS=()
STATUS_NOTE="ok"

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
  echo "[smoke] ${label}: success=${success} exit=${exit_code} ${duration_ms}ms"
}

echo "[smoke] prompt=$PROMPT_ID condition=$CONDITION automation=$AUTOMATION fixture=$FIXTURE"
echo "[smoke] scene=$SCENE"
echo "[smoke] run_dir=$RUN_DIR"

run_logged "status" status --json

finish_meta() {
  local summary="$1"
  local end_iso editor_ver success_bool errs_json
  end_iso="$(iso_now)"
  editor_ver="$(python3 -c '
import re, pathlib, sys
t = pathlib.Path(sys.argv[1]).read_text(errors="replace")
m = re.search(r"\"version\"\s*:\s*\"([^\"]+)\"", t)
print(m.group(1) if m else "")
' "$RUN_DIR/stdout.log")"
  P="$PROMPT_JSON" python3 -c '
import json, os, sys
from pathlib import Path
prompt = json.loads(os.environ["P"])
meta = {
  "prompt_id": sys.argv[1], "condition": sys.argv[2], "phase": sys.argv[3],
  "fixture": sys.argv[4], "scene": sys.argv[5], "project": sys.argv[6],
  "prompt": prompt, "automation": sys.argv[13],
  "started_at": sys.argv[7], "ended_at": sys.argv[8], "timezone": "Asia/Shanghai",
  "cli_version": sys.argv[9], "editor_version": sys.argv[10], "pipeline_port": 7800,
  "notes": sys.argv[12], "status_note": sys.argv[14],
}
Path(sys.argv[11]).write_text(json.dumps(meta, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
' "$PROMPT_ID" "$CONDITION" "$PHASE" "$FIXTURE" "$SCENE" "$PROJ" "$START_ISO" "$end_iso" "$CLI_VERSION" "$editor_ver" "$RUN_DIR/meta.json" "$summary" "$AUTOMATION" "$STATUS_NOTE"
  success_bool=false; [[ "$OVERALL_OK" -eq 1 ]] && success_bool=true
  errs_json="$(printf "%s\n" "${STEP_ERRORS[@]:-}" | python3 -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().splitlines() if l]))')"
  python3 -c '
import json, sys
from pathlib import Path
Path(sys.argv[5]).write_text(json.dumps({
  "success": sys.argv[1]=="true",
  "prompt_id": sys.argv[2],
  "condition": sys.argv[3],
  "run_dir": sys.argv[4],
  "errors": json.loads(sys.argv[6]),
  "summary": sys.argv[7],
  "automation": sys.argv[8],
  "status_note": sys.argv[9],
}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
' "$success_bool" "$PROMPT_ID" "$CONDITION" "$RUN_DIR" "$RUN_DIR/result.json" "$errs_json" "$summary" "$AUTOMATION" "$STATUS_NOTE"
  echo "[smoke] wrote $RUN_DIR"
  echo "[smoke] success=$success_bool note=$STATUS_NOTE"
  [[ "$OVERALL_OK" -eq 1 ]]
}

if [[ "$CONDITION" == "baseline" && "$AUTOMATION" != "baseline_cli" ]]; then
  STATUS_NOTE="not_automated"
  OVERALL_OK=0
  STEP_ERRORS+=("baseline_not_automated:automation=${AUTOMATION}")
  run_logged "open_scene" command --project-path "$PROJ" --format json open_scene -- --path "$SCENE" || true
  finish_meta "baseline skipped: no baseline_cli action for $PROMPT_ID"
  exit 1
fi

if [[ "$CONDITION" == "check" && "$AUTOMATION" != "check_cli" ]]; then
  STATUS_NOTE="not_automated"
  OVERALL_OK=0
  STEP_ERRORS+=("check_not_automated:automation=${AUTOMATION}")
  run_logged "open_scene" command --project-path "$PROJ" --format json open_scene -- --path "$SCENE" || true
  finish_meta "check skipped: no check_cli for $PROMPT_ID"
  exit 1
fi

run_baseline() {
  run_logged "open_scene" command --project-path "$PROJ" --format json open_scene -- --path "$SCENE"
  case "$BASELINE_ACTION" in
    move_sphere_above_cube)
      run_logged "find_CubeA" command --project-path "$PROJ" --format json --result-only find_gameobjects -- --name CubeA
      run_logged "find_SphereB" command --project-path "$PROJ" --format json --result-only find_gameobjects -- --name SphereB
      run_logged "edit_move_SphereB" command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[0,1.5,0]"
      run_logged "xform_SphereB_after" command --project-path "$PROJ" --format json --result-only get_component_properties -- --target /SphereB --type Transform
      run_logged "restore_SphereB" command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,0.5,0]"
      run_logged "save_scene" command --project-path "$PROJ" --format json save_scene -- --path "$SCENE"
      ;;
    create_cube_c)
      unity command --project-path "$PROJ" delete_gameobject -- --target /CubeC >/dev/null 2>&1 || true
      run_logged "create_CubeC" command --project-path "$PROJ" --format json create_gameobject -- --name CubeC --primitive cube
      run_logged "place_CubeC" command --project-path "$PROJ" --format json set_transform -- --target /CubeC --position "[1.5,0.5,0]"
      run_logged "find_CubeC" command --project-path "$PROJ" --format json --result-only find_gameobjects -- --name CubeC
      run_logged "verify_spacing" command --project-path "$PROJ" --format json --result-only eval -- --code 'var a=GameObject.Find("CubeA").transform.position; var c=GameObject.Find("CubeC").transform.position; var d=Vector3.Distance(a,c); return "dist="+d+":ok="+(d>1.2f && d<1.8f);'
      run_logged "delete_CubeC" command --project-path "$PROJ" --format json delete_gameobject -- --target /CubeC
      run_logged "save_scene" command --project-path "$PROJ" --format json save_scene -- --path "$SCENE"
      ;;
    raise_sphere)
      run_logged "edit_raise_SphereB" command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,2.0,0]"
      run_logged "xform_SphereB_after" command --project-path "$PROJ" --format json --result-only get_component_properties -- --target /SphereB --type Transform
      run_logged "restore_SphereB" command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,0.5,0]"
      run_logged "save_scene" command --project-path "$PROJ" --format json save_scene -- --path "$SCENE"
      ;;
    *)
      OVERALL_OK=0; STATUS_NOTE="unknown_baseline_action"
      STEP_ERRORS+=("unknown_baseline_action:$BASELINE_ACTION")
      ;;
  esac

  set +e
  MSG="$(RUN_DIR="$RUN_DIR" ACTION="$BASELINE_ACTION" python3 -c '
import json, os, pathlib, sys
by={}
for line in pathlib.Path(os.environ["RUN_DIR"],"commands.ndjson").read_text().splitlines():
  if line.strip():
    r=json.loads(line); by[r["label"]]=r
errs=[]
act=os.environ["ACTION"]
need={"move_sphere_above_cube":["edit_move_SphereB","restore_SphereB","save_scene"],
      "create_cube_c":["create_CubeC","find_CubeC","verify_spacing","delete_CubeC"],
      "raise_sphere":["edit_raise_SphereB","restore_SphereB","save_scene"]}.get(act,[])
for lab in need:
  if lab not in by: errs.append("missing:"+lab)
  elif not by[lab]["success"]: errs.append("fail:"+lab)
if act=="move_sphere_above_cube" and "1.5" not in by.get("xform_SphereB_after",{}).get("stdout_snip",""):
  errs.append("SphereB_y_check")
if act=="raise_sphere" and "2" not in by.get("xform_SphereB_after",{}).get("stdout_snip",""):
  errs.append("SphereB_raise_check")
if act=="create_cube_c":
  sn=by.get("verify_spacing",{}).get("stdout_snip","")
  if "ok=True" not in sn and "ok=true" not in sn:
    errs.append("spacing_not_ok")
sys.stdout.write(";".join(errs)); sys.exit(0 if not errs else 1)
')"
  RC=$?; set -e
  if [[ $RC -ne 0 ]]; then OVERALL_OK=0; STEP_ERRORS+=("post_check:$MSG"); fi
}

run_check() {
  run_logged "open_scene" command --project-path "$PROJ" --format json open_scene -- --path "$SCENE"
  local abs_path eval_code
  abs_path="$PROJ/${CONSTRAINT_FILE}"
  eval_code="var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@\"${abs_path}\"); return \"success=\"+r.success+\" passed=\"+r.passed+\" failed=\"+r.failed+\" skipped=\"+r.skipped+\" set=\"+r.set_id;"
  run_logged "constraint_check" command --project-path "$PROJ" --format json --result-only eval -- --code "$eval_code"
  local report_src="$PROJ/Logs/prompt2scene-check-last.json"
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
  set +e
  MSG="$(RUN_DIR="$RUN_DIR" python3 -c '
import json, pathlib, os, sys
run=pathlib.Path(os.environ["RUN_DIR"]); by={}
for line in (run/"commands.ndjson").read_text().splitlines():
  if line.strip():
    r=json.loads(line); by[r["label"]]=r
errs=[]
for lab in ["open_scene","constraint_check"]:
  if lab not in by: errs.append("missing:"+lab)
  elif not by[lab]["success"]: errs.append("fail:"+lab)
snip=by.get("constraint_check",{}).get("stdout_snip","")
if "success=True" not in snip: errs.append("eval_success_not_true")
rep=run/"check_report.json"
if rep.is_file():
  d=json.loads(rep.read_text())
  if not d.get("success"): errs.append("report_success_false")
  if int(d.get("failed",1))!=0: errs.append("report_failed")
else: errs.append("no_report")
sys.stdout.write(";".join(errs)); sys.exit(0 if not errs else 1)
')"
  RC=$?; set -e
  if [[ $RC -ne 0 ]]; then OVERALL_OK=0; STEP_ERRORS+=("post_check:$MSG"); fi
}

SUMMARY=""
case "$CONDITION" in
  baseline) run_baseline; SUMMARY="baseline_cli action=$BASELINE_ACTION" ;;
  check)    run_check; SUMMARY="check_cli file=$CONSTRAINT_FILE" ;;
esac
finish_meta "$SUMMARY"
