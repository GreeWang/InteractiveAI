#!/usr/bin/env bash
# Run formative A/B for automated prompts; record skips for automation=none.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SMOKE="$ROOT/scripts/smoke_run.sh"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai

PLAN="$ROOT/runs/_batch_plan.txt"
python3 -c '
import json
from pathlib import Path
data=json.load(open(Path.home()/"Projects/Prompt2Scene/eval/prompts/prompts.json"))
for p in data["prompts"]:
    auto=p.get("automation","none")
    if auto=="baseline_cli":
        print(p["id"]+"\tbaseline")
    elif auto=="check_cli":
        print(p["id"]+"\tcheck")
    else:
        print(p["id"]+"\tskip")
' > "$PLAN"

echo "[batch] plan:"
cat "$PLAN"

while IFS=$'\t' read -r pid cond; do
  echo "==== $pid $cond ===="
  if [[ "$cond" == "skip" ]]; then
    echo "[batch] skip $pid (not_automated)"
    continue
  fi
  set +e
  "$SMOKE" "$pid" "$cond"
  rc=$?
  set -e
  echo "[batch] $pid $cond exit=$rc"
done < "$PLAN"

python3 "$ROOT/scripts/write_ab_results.py"
