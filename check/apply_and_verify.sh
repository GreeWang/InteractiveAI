#!/usr/bin/env bash
set -euo pipefail
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
PROJ="${PROMPT2SCENE_PROJECT:-$HOME/Projects/Prompt2Scene-Baseline}"
CHECK="${HOME}/Projects/Prompt2Scene/check"
SRC="$(cd "$(dirname "$0")" && pwd)"

cp "$SRC/schema/constraint_schema_v0.2.json" "$CHECK/schema/"
cp "$SRC/constraints/F03_sample.json" "$CHECK/constraints/"
cp "$SRC/README.md" "$CHECK/README.md"
cp "$SRC/AssetsCheck/F03_sample.json" "$PROJ/Assets/Prompt2Scene/Check/Constraints/F03_sample.json"
cp "$SRC/Editor/ConstraintModels.cs" "$PROJ/Assets/Prompt2Scene/Editor/Prompt2SceneCheck/ConstraintModels.cs"
cp "$SRC/Editor/ConstraintChecker.cs" "$PROJ/Assets/Prompt2Scene/Editor/Prompt2SceneCheck/ConstraintChecker.cs"

unity command --project-path "$PROJ" open_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity
# ensure CupOnBox
if ! unity command --project-path "$PROJ" --format json --result-only find_gameobjects -- --name CupOnBox 2>/dev/null | grep -q '"count": 1'; then
  unity command --project-path "$PROJ" create_gameobject -- --name CupOnBox --primitive sphere || true
fi
unity command --project-path "$PROJ" set_transform -- --target /CupOnBox --position '[-1.5,1.25,0]' --scale '[0.4,0.4,0.4]'
unity command --project-path "$PROJ" set_transform -- --target /RedBox --rotation '[0,90,0]'
# keep positions of red/blue
unity command --project-path "$PROJ" set_transform -- --target /RedBox --position '[-1.5,0.5,0]'
unity command --project-path "$PROJ" set_transform -- --target /BlueBall --position '[1.5,0.5,0]'
unity command --project-path "$PROJ" save_scene -- --path Assets/Prompt2Scene/Fixtures/F03_ConstraintSandbox.unity

unity command --project-path "$PROJ" recompile --
for i in $(seq 1 30); do
  st=$(unity command --project-path "$PROJ" --format json --result-only recompile_status -- 2>/dev/null || true)
  echo "$st" | grep -q '"compilationFailed": true' && echo "$st" && exit 1
  echo "$st" | grep -Eq '"status": "(completed|up_to_date|idle)"' && break
  sleep 1
done

~/Projects/Prompt2Scene/eval/scripts/smoke_run.sh P04_constraint_left_of check
