#!/usr/bin/env bash
# Formal formative Round 2: P02–P09 × {baseline, check}, qwen3.8-max (Bailian), seed=1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
MAX_ROUNDS="${LLM_MAX_ROUNDS:-3}"

die() { echo "error: $*" >&2; exit 1; }
command -v unity >/dev/null || die "unity missing"
if [[ -z "${DEEPSEEK_API_KEY:-}${DASHSCOPE_API_KEY:-}${LLM_API_KEY:-}" ]]; then
  die "no API key set (DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, or LLM_API_KEY)"
fi
unity status --json | grep -q '"ready"' || die "Pipeline not ready"

# Resolve provider/model via llm_client (bailian → DASHSCOPE_MODEL; deepseek → DEEPSEEK_MODEL)
LLM_CFG_JSON="$(python3 "$SCRIPT_DIR/llm_client.py" --dotenv "$ENV_FILE" --print-config)"
export LLM_RESOLVED_PROVIDER="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["provider"])')"
export LLM_RESOLVED_MODEL="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["model"])')"
# Keep DEEPSEEK_MODEL export only when provider is deepseek (R1 path intact for reruns)
if [[ "$LLM_RESOLVED_PROVIDER" == "deepseek" ]]; then
  export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-$LLM_RESOLVED_MODEL}"
fi

BATCH_TS="$(date +%Y%m%d-%H%M%S)"
BATCH_DIR="$ROOT/runs/batch_formal_r2_${BATCH_TS}"
mkdir -p "$BATCH_DIR"
: >"$BATCH_DIR/manifest.ndjson"
echo "$BATCH_DIR" >"$ROOT/runs/.last_formal_r2_batch"
echo "[R2] provider=$LLM_RESOLVED_PROVIDER model=$LLM_RESOLVED_MODEL max_rounds=$MAX_ROUNDS seeds=1 dir=$BATCH_DIR"

restore_f02() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
  unity command --project-path "$PROJ" delete_gameobject -- --target /CubeC >/dev/null 2>&1 || true
  unity command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CubeA --position "[0,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
}

capture_f03() {
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
' >"$BATCH_DIR/f03_seed.json"
}

restore_f03() {
  SEED_JSON="$BATCH_DIR/f03_seed.json" PROJ="$PROJ" python3 <<'PY'
import json, os, re, subprocess
raw=json.load(open(os.environ["SEED_JSON"]))
text=raw.get("result") or ""
proj=os.environ["PROJ"]
subprocess.run(["unity","command","--project-path",proj,"open_scene","--","--path","Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity"], capture_output=True)
for part in text.split(";"):
    part=part.strip()
    if not part or "=MISSING" in part: continue
    m=re.match(r"([^|]+)\|pos=([^|]+)\|euler=(.+)", part)
    if not m: continue
    name,pos,euler=m.group(1),m.group(2),m.group(3)
    pos_a="["+",".join(f"{float(x):.4f}" for x in pos.split(","))+"]"
    subprocess.run(["unity","command","--project-path",proj,"set_transform","--","--target",f"/{name}","--position",pos_a], capture_output=True)
    ex,ey,ez=[float(x) for x in euler.split(",")]
    code=f'var t=GameObject.Find("{name}").transform; t.eulerAngles=new Vector3({ex}f,{ey}f,{ez}f); return "ok";'
    subprocess.run(["unity","command","--project-path",proj,"eval","--","--code",code], capture_output=True)
subprocess.run(["unity","command","--project-path",proj,"save_scene","--","--path","Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity"], capture_output=True)
print("f03_restored")
PY
}

postcheck_edit() {
  local pid="$1" out="$2"
  case "$pid" in
    P02_edit_move_sphere)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var a=GameObject.Find("CubeA").transform.position; var b=GameObject.Find("SphereB").transform.position;
var above=(b.y>a.y+0.4f)&&(Mathf.Abs(b.x-a.x)<0.6f)&&(Mathf.Abs(b.z-a.z)<0.6f);
return "pass="+above+";SphereB="+b+";CubeA="+a;' >"$out" ;;
    P03_edit_duplicate_row)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var c=GameObject.Find("CubeC"); if(c==null) return "pass=False;exists=False;dist=-1";
var a=GameObject.Find("CubeA").transform.position; var d=Vector3.Distance(a,c.transform.position);
return "pass="+(d>=1.2f&&d<=1.8f)+";exists=True;dist="+d;' >"$out" ;;
    P09_edit_raise_sphere)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var b=GameObject.Find("SphereB").transform.position;
return "pass="+(Mathf.Abs(b.y-2.0f)<0.15f)+";y="+b.y+";SphereB="+b;' >"$out" ;;
    *) echo '{"result":"skip"}' >"$out" ;;
  esac
}

postcheck_constraint() {
  local cfile="$1" out="$2"
  local abs="$PROJ/$cfile"
  unity command --project-path "$PROJ" --format json --result-only eval -- --code \
    "var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@\"${abs}\"); return \"success=\"+r.success+\" passed=\"+r.passed+\" failed=\"+r.failed;" \
    >"$out"
  local report_src="$PROJ/Logs/prompt2scene-check-last.json"
  if [[ -f "$report_src" ]]; then
    cp "$report_src" "${out%.json}_report.json"
  fi
}

PROMPTS_FILE="$ROOT/prompts/prompts.json"
CELLS=(
  P02_edit_move_sphere:baseline
  P02_edit_move_sphere:check
  P03_edit_duplicate_row:baseline
  P03_edit_duplicate_row:check
  P09_edit_raise_sphere:baseline
  P09_edit_raise_sphere:check
  P04_constraint_left_of:baseline
  P04_constraint_left_of:check
  P05_constraint_on_top:baseline
  P05_constraint_on_top:check
  P06_constraint_distance:baseline
  P06_constraint_distance:check
  P07_constraint_facing:baseline
  P07_constraint_facing:check
  P08_constraint_no_overlap:baseline
  P08_constraint_no_overlap:check
)

restore_f02
capture_f03

for cell in "${CELLS[@]}"; do
  pid="${cell%%:*}"; cond="${cell##*:}"
  echo "===== [R2] $pid × $cond ====="
  # fixture prep
  fixture="$(PROMPT_ID="$pid" PROMPTS_FILE="$PROMPTS_FILE" python3 -c 'import json,os; ps=json.load(open(os.environ["PROMPTS_FILE"]))["prompts"];
print(next(p["fixture"] for p in ps if p["id"]==os.environ["PROMPT_ID"]))')"
  cfile="$(PROMPT_ID="$pid" PROMPTS_FILE="$PROMPTS_FILE" python3 -c 'import json,os; ps=json.load(open(os.environ["PROMPTS_FILE"]))["prompts"];
p=next(x for x in ps if x["id"]==os.environ["PROMPT_ID"]); print(p.get("constraint_file") or "")')"

  if [[ "$fixture" == "F02" ]]; then restore_f02; else restore_f03; fi

  set +e
  if [[ "$cond" == "check" ]]; then
    "$SCRIPT_DIR/llm_run.sh" "$pid" check --max-rounds "$MAX_ROUNDS"
  else
    "$SCRIPT_DIR/llm_run.sh" "$pid" baseline
  fi
  rc=$?
  set -e

  run_dir="$(ls -dt "$ROOT/runs/"*"_${pid}_${cond}_llm" 2>/dev/null | head -1 || true)"
  # Score semantic/check for baseline (check condition already has multiturn final_pass)
  sem_ok=""
  sem_report=""
  rounds_used=""
  if [[ -n "$run_dir" ]]; then
    if [[ "$cond" == "check" && -f "$run_dir/multiturn_summary.json" ]]; then
      rounds_used="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("rounds_used",""))' "$run_dir/multiturn_summary.json")"
      sem_ok="$(python3 -c 'import json,sys; print("true" if json.load(open(sys.argv[1])).get("final_pass") else "false")' "$run_dir/multiturn_summary.json")"
      sem_report="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("last_report",""))' "$run_dir/multiturn_summary.json")"
    else
      rounds_used="1"
      if [[ "$fixture" == "F02" ]]; then
        postcheck_edit "$pid" "$run_dir/r1_postcheck.json"
        sem_report="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("result") or d)' "$run_dir/r1_postcheck.json" 2>/dev/null || true)"
        if echo "$sem_report" | grep -q 'pass=True'; then sem_ok=true; else sem_ok=false; fi
      else
        [[ -n "$cfile" ]] || cfile="Assets/Prompt2Scene/Check/Constraints/F03_sample.json"
        postcheck_constraint "$cfile" "$run_dir/r1_postcheck.json"
        sem_report="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("result") or d)' "$run_dir/r1_postcheck.json" 2>/dev/null || true)"
        if echo "$sem_report" | grep -q 'success=True'; then sem_ok=true; else sem_ok=false; fi
        if [[ -f "$run_dir/r1_postcheck_report.json" ]]; then
          cp "$run_dir/r1_postcheck_report.json" "$run_dir/check_report.json" 2>/dev/null || true
        fi
      fi
    fi
  fi

  PHASE="$fixture" python3 -c '
import json, os, sys, pathlib
pid, cond, rc, run_dir, batch, sem_ok, sem_report, rounds = sys.argv[1:9]
rec = {
  "prompt_id": pid,
  "condition": cond,
  "seed": 1,
  "model": os.environ.get("LLM_RESOLVED_MODEL") or os.environ.get("DEEPSEEK_MODEL","deepseek-v4-pro"),
  "llm_run_exit": int(rc),
  "run_dir": run_dir,
  "rounds_used": int(rounds) if str(rounds).isdigit() else rounds,
  "semantic_or_check_ok": sem_ok == "true",
  "notes": (sem_report or "")[:300],
  "family": "edit" if pid.startswith(("P02","P03","P09")) else "constraint",
}
harness = False
rd = pathlib.Path(run_dir) if run_dir else None
if rd and (rd/"result.json").exists():
  res = json.load(open(rd/"result.json"))
  rec["result"] = res
  harness = bool(res.get("success"))
  if cond == "check":
    # multiturn success aligned with final_pass
    harness = harness or bool(res.get("final_pass"))
if cond == "baseline":
  # harness = CLI/API executed plan ok
  harness = bool(rec.get("result",{}).get("success"))
rec["harness_ok"] = harness
# For check, prefer multiturn final_pass as semantic
if cond == "check" and rd and (rd/"multiturn_summary.json").exists():
  ms = json.load(open(rd/"multiturn_summary.json"))
  rec["semantic_or_check_ok"] = bool(ms.get("final_pass"))
  rec["rounds_used"] = ms.get("rounds_used")
  rec["notes"] = (ms.get("last_report") or "")[:300]
print(json.dumps({"prompt_id":pid,"condition":cond,"harness_ok":rec["harness_ok"],"sem_ok":rec["semantic_or_check_ok"],"rounds":rec["rounds_used"]}, ensure_ascii=False))
open(os.path.join(batch,"manifest.ndjson"),"a").write(json.dumps(rec, ensure_ascii=False)+"\n")
' "$pid" "$cond" "$rc" "$run_dir" "$BATCH_DIR" "$sem_ok" "$sem_report" "$rounds_used"

  if [[ "$fixture" == "F02" ]]; then restore_f02; else restore_f03; fi
done

restore_f02
restore_f03
echo "[R2] done → $BATCH_DIR"
