#!/usr/bin/env bash
# Multi-seed P02–P09 for one provider. Usage: run_formal_multiseed.sh ds|qwen [seeds]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
MODE="${1:-ds}"
SEEDS="${2:-2,3}"
if [[ "$MODE" == "ds" || "$MODE" == "deepseek" ]]; then
  export LLM_PROVIDER=deepseek
  export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-v4-pro}"
  export FORMAL_TAG=multiseed_ds
elif [[ "$MODE" == "qwen" || "$MODE" == "bailian" ]]; then
  export LLM_PROVIDER=bailian
  export DASHSCOPE_MODEL="${DASHSCOPE_MODEL:-qwen3.8-max}"
  export FORMAL_TAG=multiseed_qwen
else
  echo "usage: $0 ds|qwen [seeds]" >&2; exit 2
fi
export FORMAL_PROMPTS=P02_edit_move_sphere,P03_edit_duplicate_row,P09_edit_raise_sphere,P04_constraint_left_of,P05_constraint_on_top,P06_constraint_distance,P07_constraint_facing,P08_constraint_no_overlap
export FORMAL_CONDITIONS=baseline,check
export FORMAL_SEEDS="$SEEDS"
exec "$(dirname "$0")/run_formal_batch.sh"
