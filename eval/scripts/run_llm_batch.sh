#!/usr/bin/env bash
# Formative LLM batch (deepseek-v4-pro by default via eval/.env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
if [[ -z "${DEEPSEEK_API_KEY:-}${DASHSCOPE_API_KEY:-}${LLM_API_KEY:-}" ]]; then
  echo "error: no API key set (DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, or LLM_API_KEY)" >&2
  exit 1
fi

die() { echo "error: $*" >&2; exit 1; }
command -v unity >/dev/null || die "unity CLI missing"
[[ -d "$PROJ" ]] || die "project missing: $PROJ"

unity status --json | grep -q '"state"[[:space:]]*:[[:space:]]*"ready"' || die "Pipeline not ready on 7800"

BATCH_TS="$(date +%Y%m%d-%H%M%S)"
BATCH_DIR="$ROOT/runs/batch_llm_${BATCH_TS}"
mkdir -p "$BATCH_DIR"
MANIFEST="$BATCH_DIR/manifest.ndjson"
: >"$MANIFEST"

restore_f02() {
  echo "[batch] restore F02"
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
  unity command --project-path "$PROJ" delete_gameobject -- --target /CubeC >/dev/null 2>&1 || true
  unity command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CubeA --position "[0,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
}

# Seed captured at batch start (written by caller or self)
F03_SEED_FILE="$BATCH_DIR/f03_seed.json"
capture_f03_seed() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var names=new string[]{"RedBox","BlueBall","CupOnBox"};
var sb=new System.Text.StringBuilder();
foreach(var n in names){
  var go=GameObject.Find(n);
  if(go==null){ sb.Append(n+"=MISSING;"); continue; }
  var t=go.transform;
  sb.Append(n+"|pos="+t.position.x+","+t.position.y+","+t.position.z+"|euler="+t.eulerAngles.x+","+t.eulerAngles.y+","+t.eulerAngles.z+";");
}
return sb.ToString();
' >"$F03_SEED_FILE"
}

restore_f03() {
  echo "[batch] restore F03 from seed"
  [[ -f "$F03_SEED_FILE" ]] || return 0
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  # Parse seed and apply via python→unity
  SEED_JSON="$F03_SEED_FILE" PROJ="$PROJ" python3 <<'PY'
import json, os, re, subprocess
raw = json.load(open(os.environ["SEED_JSON"]))
text = raw.get("result") or ""
proj = os.environ["PROJ"]
for part in text.split(";"):
    part=part.strip()
    if not part or "=MISSING" in part: continue
    m=re.match(r"([^|]+)\|pos=([^|]+)\|euler=(.+)", part)
    if not m: continue
    name, pos, euler = m.group(1), m.group(2), m.group(3)
    pos_a = "[" + ",".join(f"{float(x):.4f}" for x in pos.split(",")) + "]"
    # set position
    subprocess.run(["unity","command","--project-path",proj,"set_transform","--","--target",f"/{name}","--position",pos_a],
                   capture_output=True, text=True)
    # rotation via eval for reliability
    ex,ey,ez = [float(x) for x in euler.split(",")]
    code = f'var t=GameObject.Find("{name}").transform; t.eulerAngles=new Vector3({ex}f,{ey}f,{ez}f); return "ok";'
    subprocess.run(["unity","command","--project-path",proj,"eval","--","--code",code], capture_output=True, text=True)
subprocess.run(["unity","command","--project-path",proj,"save_scene","--","--path","Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity"],
               capture_output=True, text=True)
print("f03_restored")
PY
}

postcheck_edit() {
  local prompt_id="$1" run_dir="$2"
  local out="$run_dir/postcheck.json"
  case "$prompt_id" in
    P02_edit_move_sphere)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var a=GameObject.Find("CubeA").transform.position;
var b=GameObject.Find("SphereB").transform.position;
var above=(b.y>a.y+0.4f) && (Mathf.Abs(b.x-a.x)<0.6f) && (Mathf.Abs(b.z-a.z)<0.6f);
return "above="+above+";SphereB="+b+";CubeA="+a;
' >"$out" 2>&1 || true
      ;;
    P03_edit_duplicate_row)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var c=GameObject.Find("CubeC");
if(c==null) return "exists=False;dist=-1";
var a=GameObject.Find("CubeA").transform.position;
var d=Vector3.Distance(a,c.transform.position);
var ok=(d>1.2f && d<1.8f);
return "exists=True;dist="+d+";ok="+ok;
' >"$out" 2>&1 || true
      ;;
    P09_edit_raise_sphere)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var b=GameObject.Find("SphereB").transform.position;
var ok=Mathf.Abs(b.y-2.0f)<0.15f;
return "y="+b.y+";ok="+ok+";SphereB="+b;
' >"$out" 2>&1 || true
      ;;
    *) echo '{"skipped":true}' >"$out" ;;
  esac
}

PROMPTS=(
  "P02_edit_move_sphere:baseline"
  "P03_edit_duplicate_row:baseline"
  "P09_edit_raise_sphere:baseline"
  "P04_constraint_left_of:check"
  "P05_constraint_on_top:check"
  "P06_constraint_distance:check"
  "P07_constraint_facing:check"
  "P08_constraint_no_overlap:check"
)

echo "[batch] model=${DEEPSEEK_MODEL:-deepseek-v4-pro} ts=$BATCH_TS"
echo "[batch] dir=$BATCH_DIR"
restore_f02
capture_f03_seed

for item in "${PROMPTS[@]}"; do
  pid="${item%%:*}"
  cond="${item##*:}"
  echo "===== [batch] $pid $cond ====="
  set +e
  "$SCRIPT_DIR/llm_run.sh" "$pid" "$cond"
  rc=$?
  set -e
  # newest matching run dir
  run_dir="$(ls -dt "$ROOT/runs/"*"_${pid}_${cond}_llm" 2>/dev/null | head -1 || true)"
  semantic=""
  if [[ -n "$run_dir" && "$cond" == "baseline" ]]; then
    postcheck_edit "$pid" "$run_dir"
  fi
  python3 -c '
import json, os, sys, pathlib
pid, cond, rc, run_dir, batch = sys.argv[1:6]
rec = {"prompt_id": pid, "condition": cond, "llm_run_exit": int(rc), "run_dir": run_dir}
if run_dir and pathlib.Path(run_dir, "result.json").exists():
  rec["result"] = json.load(open(pathlib.Path(run_dir)/"result.json"))
if run_dir and pathlib.Path(run_dir, "plan.json").exists():
  plan=json.load(open(pathlib.Path(run_dir)/"plan.json"))
  rec["n_commands"] = len(plan.get("commands") or [])
if run_dir and pathlib.Path(run_dir, "check_report.json").exists():
  rep=json.load(open(pathlib.Path(run_dir)/"check_report.json"))
  rec["check_success"] = bool(rep.get("success"))
  rec["check_passed"] = rep.get("passed")
  rec["check_failed"] = rep.get("failed")
if run_dir and pathlib.Path(run_dir, "postcheck.json").exists():
  try:
    pc=json.load(open(pathlib.Path(run_dir)/"postcheck.json"))
    rec["postcheck"] = pc.get("result") or pc
  except Exception as e:
    rec["postcheck_error"]=str(e)
# semantic pass heuristic
ok = False
if cond=="check":
  ok = bool(rec.get("check_success"))
elif cond=="baseline":
  s = str(rec.get("postcheck") or "")
  if pid.startswith("P02") and "above=True" in s: ok=True
  elif pid.startswith("P03") and "exists=True" in s and ("ok=True" in s or "ok=true" in s): ok=True
  elif pid.startswith("P09") and "ok=True" in s: ok=True
  elif rec.get("result",{}).get("success") and rec.get("n_commands",0)>0:
    # commands ran but semantic unknown
    ok = False
    rec["semantic_note"]="commands_ok_but_criteria_unmet_or_unclear"
rec["semantic_pass"]=ok
rec["harness_success"]=bool(rec.get("result",{}).get("success"))
print(json.dumps(rec, ensure_ascii=False))
open(os.path.join(batch,"manifest.ndjson"),"a").write(json.dumps(rec, ensure_ascii=False)+"\n")
' "$pid" "$cond" "$rc" "$run_dir" "$BATCH_DIR"

  # restore fixtures after each prompt
  if [[ "$cond" == "baseline" ]]; then
    restore_f02
  else
    restore_f03
  fi
done

restore_f02
restore_f03
echo "$BATCH_DIR" >"$ROOT/runs/.last_llm_batch"
echo "[batch] done → $BATCH_DIR"
