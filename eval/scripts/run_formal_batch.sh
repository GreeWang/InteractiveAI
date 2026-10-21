#!/usr/bin/env bash
# Generic formal batch: prompts × conditions × seeds via env.
# Env:
#   FORMAL_TAG          batch name suffix (required), e.g. r3_gen / multiseed_ds / r2_retry
#   FORMAL_PROMPTS      comma list (default P02..P09)
#   FORMAL_CONDITIONS   comma list (default baseline,check)
#   FORMAL_SEEDS        comma list (default 1)
#   LLM_MAX_ROUNDS      default 3
#   LLM_PROVIDER / DASHSCOPE_* / DEEPSEEK_* via eval/.env
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ENV_FILE="$ROOT/.env"
_PRESERVE_KEYS=(LLM_PROVIDER LLM_API_KEY LLM_BASE_URL LLM_MODEL DEEPSEEK_MODEL DASHSCOPE_MODEL DASHSCOPE_BASE_URL DEEPSEEK_BASE_URL LLM_SEED FORMAL_TAG FORMAL_PROMPTS FORMAL_CONDITIONS FORMAL_SEEDS)
_PRESERVED=()
for _k in "${_PRESERVE_KEYS[@]}"; do
  if [[ -n "${!_k+x}" ]]; then _PRESERVED+=("$_k=${!_k}"); fi
done
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
for _kv in "${_PRESERVED[@]:-}"; do export "$_kv"; done
unset _k _kv _PRESERVED _PRESERVE_KEYS
MAX_ROUNDS="${LLM_MAX_ROUNDS:-3}"
TAG="${FORMAL_TAG:?set FORMAL_TAG}"
PROMPTS_CSV="${FORMAL_PROMPTS:-P02_edit_move_sphere,P03_edit_duplicate_row,P09_edit_raise_sphere,P04_constraint_left_of,P05_constraint_on_top,P06_constraint_distance,P07_constraint_facing,P08_constraint_no_overlap}"
CONDS_CSV="${FORMAL_CONDITIONS:-baseline,check}"
SEEDS_CSV="${FORMAL_SEEDS:-1}"

die() { echo "error: $*" >&2; exit 1; }
command -v unity >/dev/null || die "unity missing"
if [[ -z "${DEEPSEEK_API_KEY:-}${DASHSCOPE_API_KEY:-}${LLM_API_KEY:-}" ]]; then
  die "no API key set"
fi
unity status --json | grep -q '"ready"' || die "Pipeline not ready"

LLM_CFG_JSON="$(python3 "$SCRIPT_DIR/llm_client.py" --dotenv "$ENV_FILE" --print-config)"
export LLM_RESOLVED_PROVIDER="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["provider"])')"
export LLM_RESOLVED_MODEL="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["model"])')"

BATCH_TS="$(date +%Y%m%d-%H%M%S)"
BATCH_DIR="$ROOT/runs/batch_formal_${TAG}_${BATCH_TS}"
mkdir -p "$BATCH_DIR"
: >"$BATCH_DIR/manifest.ndjson"
echo "$BATCH_DIR" >"$ROOT/runs/.last_formal_${TAG}_batch"
echo "[formal/$TAG] provider=$LLM_RESOLVED_PROVIDER model=$LLM_RESOLVED_MODEL seeds=$SEEDS_CSV prompts=$PROMPTS_CSV conds=$CONDS_CSV dir=$BATCH_DIR"

IFS=',' read -r -a PROMPTS <<<"$PROMPTS_CSV"
IFS=',' read -r -a CONDS <<<"$CONDS_CSV"
IFS=',' read -r -a SEEDS <<<"$SEEDS_CSV"

restore_f01() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F01_EmptyRoom.unity >/dev/null
  unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var roots = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
foreach(var go in roots){ UnityEngine.Object.DestroyImmediate(go); }
UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
return "cleared="+roots.Length;' >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F01_EmptyRoom.unity >/dev/null
}

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

# Displace CupOnBox so on_top is a real placement task (seed often already passes).
prep_p05() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CupOnBox --position "[0,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  echo "[formal] P05 prep: CupOnBox → [0,0.5,0]"
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
    P01_generate_table)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var table=GameObject.Find("Table"); var cup=GameObject.Find("Cup");
if(table==null||cup==null) return "pass=False;exists=False;detail=missing";
var tb=table.transform.position; var cp=cup.transform.position;
var horiz=Vector2.Distance(new Vector2(cp.x,cp.z), new Vector2(tb.x,tb.z));
var dy=cp.y-tb.y;
var ok=(horiz<=0.5f)&&(dy>=0.3f)&&(dy<=1.5f);
return "pass="+ok+";exists=True;horiz="+horiz+";dy="+dy+";Table="+tb+";Cup="+cp;' >"$out" ;;
    P10_generate_row)
      unity command --project-path "$PROJ" --format json --result-only eval -- --code '
var a=GameObject.Find("A"); var b=GameObject.Find("B"); var c=GameObject.Find("C");
if(a==null||b==null||c==null) return "pass=False;exists=False;detail=missing_ABC";
var pa=a.transform.position; var pb=b.transform.position; var pc=c.transform.position;
var d1=Vector3.Distance(pa,pb); var d2=Vector3.Distance(pb,pc);
var ok=(d1>=0.8f&&d1<=1.2f)&&(d2>=0.8f&&d2<=1.2f);
return "pass="+ok+";exists=True;dAB="+d1+";dBC="+d2+";A="+pa+";B="+pb+";C="+pc;' >"$out" ;;
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

# Ensure F03 seed captured from clean fixture
restore_f02
restore_f01
# Reset F03 Cup to known good then capture (prep will displace per P05 cell)
unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
unity command --project-path "$PROJ" --format json set_transform -- --target /RedBox --position "[-1.5,0.5,0]" >/dev/null
unity command --project-path "$PROJ" --format json set_transform -- --target /BlueBall --position "[1.5,0.5,0]" >/dev/null
unity command --project-path "$PROJ" --format json set_transform -- --target /CupOnBox --position "[-1.5,1.25,0]" >/dev/null
unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
capture_f03

for seed in "${SEEDS[@]}"; do
  for pid in "${PROMPTS[@]}"; do
    for cond in "${CONDS[@]}"; do
      echo "===== [formal/$TAG] seed=$seed $pid × $cond ====="
      fixture="$(PROMPT_ID="$pid" PROMPTS_FILE="$PROMPTS_FILE" python3 -c 'import json,os; ps=json.load(open(os.environ["PROMPTS_FILE"]))["prompts"];
print(next(p["fixture"] for p in ps if p["id"]==os.environ["PROMPT_ID"]))')"
      cfile="$(PROMPT_ID="$pid" PROMPTS_FILE="$PROMPTS_FILE" python3 -c 'import json,os; ps=json.load(open(os.environ["PROMPTS_FILE"]))["prompts"];
p=next(x for x in ps if x["id"]==os.environ["PROMPT_ID"]); print(p.get("constraint_file") or "")')"
      phase="$(PROMPT_ID="$pid" PROMPTS_FILE="$PROMPTS_FILE" python3 -c 'import json,os; ps=json.load(open(os.environ["PROMPTS_FILE"]))["prompts"];
print(next(p.get("phase","") for p in ps if p["id"]==os.environ["PROMPT_ID"]))')"

      case "$fixture" in
        F01) restore_f01 ;;
        F02) restore_f02 ;;
        F03) restore_f03 ;;
      esac
      if [[ "$pid" == "P05_constraint_on_top" ]]; then
        prep_p05
      fi

      export LLM_SEED="$seed"
      set +e
      if [[ "$cond" == "check" ]]; then
        "$SCRIPT_DIR/llm_run.sh" "$pid" check --max-rounds "$MAX_ROUNDS"
      else
        "$SCRIPT_DIR/llm_run.sh" "$pid" baseline
      fi
      rc=$?
      set -e

      run_dir="$(ls -dt "$ROOT/runs/"*"_${pid}_${cond}_llm" 2>/dev/null | head -1 || true)"
      sem_ok=""; sem_report=""; rounds_used=""
      if [[ -n "$run_dir" ]]; then
        if [[ "$cond" == "check" && -f "$run_dir/multiturn_summary.json" ]]; then
          rounds_used="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("rounds_used",""))' "$run_dir/multiturn_summary.json")"
          sem_ok="$(python3 -c 'import json,sys; print("true" if json.load(open(sys.argv[1])).get("final_pass") else "false")' "$run_dir/multiturn_summary.json")"
          sem_report="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("last_report",""))' "$run_dir/multiturn_summary.json")"
        else
          rounds_used="1"
          if [[ "$fixture" == "F03" && -n "$cfile" ]]; then
            postcheck_constraint "$cfile" "$run_dir/r1_postcheck.json"
            sem_report="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("result") or d)' "$run_dir/r1_postcheck.json" 2>/dev/null || true)"
            if echo "$sem_report" | grep -q 'success=True'; then sem_ok=true; else sem_ok=false; fi
            [[ -f "$run_dir/r1_postcheck_report.json" ]] && cp "$run_dir/r1_postcheck_report.json" "$run_dir/check_report.json" 2>/dev/null || true
          else
            postcheck_edit "$pid" "$run_dir/r1_postcheck.json"
            sem_report="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("result") or d)' "$run_dir/r1_postcheck.json" 2>/dev/null || true)"
            if echo "$sem_report" | grep -q 'pass=True'; then sem_ok=true; else sem_ok=false; fi
          fi
        fi
      fi

      FAMILY="constraint"
      [[ "$phase" == "edit" || "$pid" == P02* || "$pid" == P03* || "$pid" == P09* ]] && FAMILY="edit"
      [[ "$phase" == "generate" || "$pid" == P01* || "$pid" == P10* ]] && FAMILY="generate"

      python3 -c '
import json, os, sys, pathlib
pid, cond, rc, run_dir, batch, sem_ok, sem_report, rounds, seed, family = sys.argv[1:11]
rec = {
  "prompt_id": pid,
  "condition": cond,
  "seed": int(seed),
  "model": os.environ.get("LLM_RESOLVED_MODEL") or "",
  "provider": os.environ.get("LLM_RESOLVED_PROVIDER") or "",
  "llm_run_exit": int(rc),
  "run_dir": run_dir,
  "rounds_used": int(rounds) if str(rounds).isdigit() else rounds,
  "semantic_or_check_ok": sem_ok == "true",
  "notes": (sem_report or "")[:400],
  "family": family,
  "tag": os.environ.get("FORMAL_TAG",""),
}
harness = False
rd = pathlib.Path(run_dir) if run_dir else None
if rd and (rd/"result.json").exists():
  res = json.load(open(rd/"result.json"))
  rec["result"] = res
  harness = bool(res.get("success"))
  if cond == "check":
    harness = harness or bool(res.get("final_pass"))
if cond == "baseline":
  harness = bool(rec.get("result",{}).get("success"))
rec["harness_ok"] = harness
if cond == "check" and rd and (rd/"multiturn_summary.json").exists():
  ms = json.load(open(rd/"multiturn_summary.json"))
  rec["semantic_or_check_ok"] = bool(ms.get("final_pass"))
  rec["rounds_used"] = ms.get("rounds_used")
  rec["notes"] = (ms.get("last_report") or "")[:400]
print(json.dumps({"seed":int(seed),"prompt_id":pid,"condition":cond,"harness_ok":rec["harness_ok"],"sem_ok":rec["semantic_or_check_ok"],"rounds":rec["rounds_used"]}, ensure_ascii=False))
open(os.path.join(batch,"manifest.ndjson"),"a").write(json.dumps(rec, ensure_ascii=False)+"\n")
' "$pid" "$cond" "$rc" "$run_dir" "$BATCH_DIR" "$sem_ok" "$sem_report" "$rounds_used" "$seed" "$FAMILY"

      case "$fixture" in
        F01) restore_f01 ;;
        F02) restore_f02 ;;
        F03) restore_f03 ;;
      esac
    done
  done
done

restore_f01
restore_f02
restore_f03
echo "[formal/$TAG] done → $BATCH_DIR"
