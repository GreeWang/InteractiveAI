#!/usr/bin/env bash
# Closeout batch: task matrix / held-out A/B / ablation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
ENV_FILE="$ROOT/.env"

_PRESERVE_KEYS=(LLM_PROVIDER LLM_API_KEY LLM_BASE_URL LLM_MODEL DEEPSEEK_MODEL DASHSCOPE_MODEL DASHSCOPE_BASE_URL DEEPSEEK_BASE_URL LLM_SEED FORMAL_TAG FORMAL_PROMPTS FORMAL_CONDITIONS FORMAL_SEEDS PROMPTS_FILE)
_PRESERVED=()
for _k in "${_PRESERVE_KEYS[@]}"; do
  if [[ -n "${!_k+x}" ]]; then _PRESERVED+=("$_k=${!_k}"); fi
done
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
for _kv in "${_PRESERVED[@]:-}"; do export "$_kv"; done
unset _k _kv _PRESERVED _PRESERVE_KEYS

MAX_ROUNDS="${LLM_MAX_ROUNDS:-3}"
TAG="${FORMAL_TAG:?set FORMAL_TAG}"
BASE_PROMPTS_FILE="${PROMPTS_FILE:-$ROOT/prompts/prompts.json}"
PROMPTS_CSV="${FORMAL_PROMPTS:?set FORMAL_PROMPTS}"
CONDS_CSV="${FORMAL_CONDITIONS:-baseline,check}"
SEEDS_CSV="${FORMAL_SEEDS:-1}"

die() { echo "error: $*" >&2; exit 1; }
command -v unity >/dev/null || die "unity missing"
[[ -f "$BASE_PROMPTS_FILE" ]] || die "prompts missing: $BASE_PROMPTS_FILE"
if [[ -z "${DEEPSEEK_API_KEY:-}${DASHSCOPE_API_KEY:-}${LLM_API_KEY:-}" ]]; then die "no API key"; fi
unity status --json | grep -q '"ready"' || die "Pipeline not ready"

LLM_CFG_JSON="$(python3 "$SCRIPT_DIR/llm_client.py" --dotenv "$ENV_FILE" --print-config)"
PROVIDER="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["provider"])')"
MODEL="$(printf '%s' "$LLM_CFG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["model"])')"

BATCH_TS="$(date +%Y%m%d-%H%M%S)"
BATCH_DIR="$ROOT/runs/batch_${TAG}_${BATCH_TS}"
mkdir -p "$BATCH_DIR"
: >"$BATCH_DIR/manifest.ndjson"
echo "$BATCH_DIR" >"$ROOT/runs/.last_${TAG}_batch"
echo "[closeout/$TAG] provider=$PROVIDER model=$MODEL seeds=$SEEDS_CSV prompts=$PROMPTS_CSV conds=$CONDS_CSV file=$BASE_PROMPTS_FILE dir=$BATCH_DIR"

IFS=',' read -r -a PROMPTS <<<"$PROMPTS_CSV"
IFS=',' read -r -a CONDS <<<"$CONDS_CSV"
IFS=',' read -r -a SEEDS <<<"$SEEDS_CSV"

restore_f01() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F01_EmptyRoom.unity >/dev/null
  unity command --project-path "$PROJ" --format json --result-only eval -- --code 'var roots = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects(); foreach(var go in roots){ UnityEngine.Object.DestroyImmediate(go); } UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty(); return "cleared="+roots.Length;' >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F01_EmptyRoom.unity >/dev/null
}
restore_f02() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
  unity command --project-path "$PROJ" delete_gameobject -- --target /CubeC >/dev/null 2>&1 || true
  unity command --project-path "$PROJ" delete_gameobject -- --target /SideCube >/dev/null 2>&1 || true
  unity command --project-path "$PROJ" --format json set_transform -- --target /SphereB --position "[1.5,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CubeA --position "[0,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F02_EditBaseline.unity >/dev/null
}
restore_f03_seed() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /RedBox --position "[-1.5,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /BlueBall --position "[1.5,0.5,0]" >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CupOnBox --position "[-1.5,1.25,0]" --scale "[0.4,0.4,0.4]" >/dev/null
  unity command --project-path "$PROJ" --format json --result-only eval -- --code 'var t=GameObject.Find("RedBox").transform; t.eulerAngles=new Vector3(0f,90f,0f); return "ok";' >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
}
prep_displace_cup() {
  unity command --project-path "$PROJ" --format json open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
  unity command --project-path "$PROJ" --format json set_transform -- --target /CupOnBox --position "[0,0.5,0]" --scale "[0.4,0.4,0.4]" >/dev/null
  unity command --project-path "$PROJ" --format json save_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity >/dev/null
}

write_skill_prompts() {
  python3 - "$1" "$BASE_PROMPTS_FILE" "$2" <<'PY'
import json, sys
pid, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.load(open(src))
rich = ("\nSkill-rich extras (NO deterministic Check loop): prefer catalog names; "
        "for on_top match support X/Z exactly and y≈support.y+0.75; "
        "never assume supports are at world origin; keep locked objects fixed; "
        "avoid origin keep-out |x|,|z|≤0.75; F02 CubeA(0,0.5,0) SphereB(1.5,0.5,0); "
        "F03 RedBox(-1.5,0.5,0) BlueBall(1.5,0.5,0).")
out = {"version": data.get("version", "0"), "prompts": []}
for p in data["prompts"]:
    q = dict(p)
    if q["id"] == pid:
        q["llm_hint"] = (q.get("llm_hint") or "") + rich
    out["prompts"].append(q)
json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)
PY
}

postcheck_any() {
  # args: mode pid cfile out -> prints true/false
  PROJ="$PROJ" python3 "$SCRIPT_DIR/closeout_postcheck.py" "$@"
}

append_manifest() {
  python3 - "$BATCH_DIR" "$TAG" "$pid" "$cond" "$seed" "$PROVIDER" "$MODEL" "$fixture" "$cfile" "$rc" "$sem_ok" "$rounds_used" "$n_cmds" "$wall_ms" "$prompt_tok" "$compl_tok" "$total_tok" "$run_dir" "$sem_report" <<'PY'
import json, sys, time
(batch, tag, pid, cond, seed, provider, model, fixture, cfile, rc, sem_ok, rounds, ncmds, wall, ptok, ctok, ttok, rundir, report) = sys.argv[1:]
rec = {
  "tag": tag, "prompt_id": pid, "condition": cond, "seed": int(seed),
  "provider": provider, "model": model, "fixture": fixture, "constraint_file": cfile,
  "rc": int(rc or 0), "semantic_ok": sem_ok == "true", "rounds_used": rounds,
  "n_commands": int(ncmds or 0), "wall_ms": int(wall or 0),
  "prompt_tokens": int(ptok or 0), "completion_tokens": int(ctok or 0), "total_tokens": int(ttok or 0),
  "run_dir": rundir, "report": (report or "").replace("\n", " ")[:500],
  "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
open(batch + "/manifest.ndjson", "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
print(json.dumps({"cell": pid, "cond": cond, "seed": int(seed), "ok": rec["semantic_ok"], "wall_ms": rec["wall_ms"]}, ensure_ascii=False))
PY
}

for seed in "${SEEDS[@]}"; do
  for pid in "${PROMPTS[@]}"; do
    for cond in "${CONDS[@]}"; do
      echo "===== [closeout/$TAG] seed=$seed $pid × $cond ====="
      cell_start="$(python3 -c 'import time; print(int(time.time()*1000))')"
      meta_json="$(python3 - "$pid" "$BASE_PROMPTS_FILE" <<'PY'
import json, sys
pid, path = sys.argv[1], sys.argv[2]
p = next(x for x in json.load(open(path))["prompts"] if x["id"] == pid)
print(json.dumps({"fixture": p.get("fixture",""), "cfile": p.get("constraint_file") or "", "prep": p.get("prep") or ""}))
PY
)"
      fixture="$(printf '%s' "$meta_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["fixture"])')"
      cfile="$(printf '%s' "$meta_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cfile"])')"
      prep="$(printf '%s' "$meta_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["prep"])')"
      case "$fixture" in
        F01) restore_f01 ;;
        F02) restore_f02 ;;
        F03) restore_f03_seed ;;
      esac
      if [[ "$pid" == "P05_constraint_on_top" || "$pid" == "P11_constraint_clearance" || "$pid" == H05* || "$pid" == H11* || "$prep" == "displace_cup_origin" ]]; then
        prep_displace_cup
      fi
      run_prompts="$BASE_PROMPTS_FILE"
      run_cond="$cond"
      if [[ "$cond" == "skill" ]]; then
        run_prompts="$BATCH_DIR/prompts_skill_${pid}_s${seed}.json"
        write_skill_prompts "$pid" "$run_prompts"
        run_cond="baseline"
      fi
      export LLM_SEED="$seed"
      export PROMPTS_FILE="$run_prompts"
      set +e
      "$SCRIPT_DIR/llm_run.sh" "$pid" "$run_cond" --max-rounds "$MAX_ROUNDS"
      rc=$?
      set -e
      run_dir="$(ls -dt "$ROOT/runs/"*"_${pid}_${run_cond}_llm" 2>/dev/null | head -1 || true)"
      sem_ok="false"; rounds_used=""; sem_report=""; n_cmds=0
      prompt_tok=0; compl_tok=0; total_tok=0
      if [[ -n "$run_dir" && -d "$run_dir" ]]; then
        ln -sfn "$run_dir" "$BATCH_DIR/${pid}__${cond}__seed${seed}" 2>/dev/null || true
        if [[ "$cond" == "check" && -f "$run_dir/multiturn_summary.json" ]]; then
          rounds_used="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("rounds_used",""))' "$run_dir/multiturn_summary.json")"
          sem_ok="$(python3 -c 'import json,sys; print("true" if json.load(open(sys.argv[1])).get("final_pass") else "false")' "$run_dir/multiturn_summary.json")"
          sem_report="$(python3 -c 'import json,sys; print(str(json.load(open(sys.argv[1])).get("last_report",""))[:500])' "$run_dir/multiturn_summary.json")"
        else
          rounds_used="1"
          if [[ "$fixture" == "F03" && -n "$cfile" ]]; then
            sem_ok="$(postcheck_any constraint "$pid" "$cfile" "$run_dir/postcheck.json")"
          else
            sem_ok="$(postcheck_any edit "$pid" "" "$run_dir/postcheck.json")"
          fi
          sem_report="$(python3 -c 'import sys; print(open(sys.argv[1]).read()[:500])' "$run_dir/postcheck.json")"
        fi
        if [[ -f "$run_dir/commands.ndjson" ]]; then
          n_cmds="$(wc -l <"$run_dir/commands.ndjson" | tr -d ' ')"
        elif [[ -f "$run_dir/plan.json" ]]; then
          n_cmds="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1])).get("commands") or []))' "$run_dir/plan.json")"
        fi
        usage="$(python3 - "$run_dir" <<'PY'
import json, sys
from pathlib import Path
rd = Path(sys.argv[1]); pt=ct=tt=0
for p in list(rd.glob("round_*/llm_response.json")) + [rd / "llm_response.json"]:
    if not p.is_file():
        continue
    try: d=json.loads(p.read_text(encoding="utf-8"))
    except Exception: continue
    u=d.get("usage") or {}
    if u:
        pt += int(u.get("prompt_tokens") or 0); ct += int(u.get("completion_tokens") or 0)
        tt += int(u.get("total_tokens") or (int(u.get("prompt_tokens") or 0)+int(u.get("completion_tokens") or 0)))
print(f"{pt},{ct},{tt}")
PY
)"
        prompt_tok="$(echo "$usage" | cut -d, -f1)"
        compl_tok="$(echo "$usage" | cut -d, -f2)"
        total_tok="$(echo "$usage" | cut -d, -f3)"
      fi
      cell_end="$(python3 -c 'import time; print(int(time.time()*1000))')"
      wall_ms=$((cell_end - cell_start))
      append_manifest
    done
  done
done

echo "[closeout/$TAG] DONE $BATCH_DIR"
