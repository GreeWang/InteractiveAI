#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
MAX_ROUNDS="${LLM_MAX_ROUNDS:-3}"

unity status --json | grep -q '"ready"' || { echo "Pipeline not ready"; exit 1; }

BATCH_TS="$(date +%Y%m%d-%H%M%S)"
BATCH_DIR="$ROOT/runs/batch_llm_multiturn_${BATCH_TS}"
mkdir -p "$BATCH_DIR"
: >"$BATCH_DIR/manifest.ndjson"
echo "$BATCH_DIR" >"$ROOT/runs/.last_llm_multiturn_batch"

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

echo "[mt-batch] model=${DEEPSEEK_MODEL} max_rounds=$MAX_ROUNDS dir=$BATCH_DIR"
restore_f02
capture_f03

PROMPTS=(
  "P02_edit_move_sphere:check"
  "P03_edit_duplicate_row:check"
  "P09_edit_raise_sphere:check"
  "P04_constraint_left_of:check"
)

for item in "${PROMPTS[@]}"; do
  pid="${item%%:*}"; cond="${item##*:}"
  echo "===== [mt-batch] $pid $cond ====="
  restore_f02
  # For F03 prompts restore f03 first
  if [[ "$pid" == P04* || "$pid" == P05* || "$pid" == P06* || "$pid" == P07* || "$pid" == P08* ]]; then
    restore_f03
  fi
  set +e
  "$SCRIPT_DIR/llm_run.sh" "$pid" "$cond" --max-rounds "$MAX_ROUNDS"
  rc=$?
  set -e
  run_dir="$(ls -dt "$ROOT/runs/"*"_${pid}_${cond}_llm" 2>/dev/null | head -1 || true)"
  python3 -c '
import json,sys,pathlib,os
pid,cond,rc,run_dir,batch=sys.argv[1:6]
rec={"prompt_id":pid,"condition":cond,"llm_run_exit":int(rc),"run_dir":run_dir}
rd=pathlib.Path(run_dir) if run_dir else None
if rd and (rd/"result.json").exists():
  rec["result"]=json.load(open(rd/"result.json"))
if rd and (rd/"multiturn_summary.json").exists():
  ms=json.load(open(rd/"multiturn_summary.json"))
  rec["final_pass"]=ms.get("final_pass")
  rec["rounds_used"]=ms.get("rounds_used")
  rec["rounds"]=ms.get("rounds")
  rec["last_report"]=ms.get("last_report")
print(json.dumps({k:rec.get(k) for k in ("prompt_id","final_pass","rounds_used","llm_run_exit")}, ensure_ascii=False))
open(os.path.join(batch,"manifest.ndjson"),"a").write(json.dumps(rec, ensure_ascii=False)+"\n")
' "$pid" "$cond" "$rc" "$run_dir" "$BATCH_DIR"
  if [[ "$pid" == P0[2349]* ]]; then restore_f02; else restore_f03; fi
done

restore_f02
restore_f03
echo "[mt-batch] done $BATCH_DIR"
