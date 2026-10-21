#!/usr/bin/env bash
# Formal generate slice: P01/P10 × baseline/check × current provider model, seed=1
# Caller sets LLM_PROVIDER / model; or pass MODEL_TAG=ds|qwen
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
MODE="${1:-}"
if [[ "$MODE" == "ds" || "$MODE" == "deepseek" ]]; then
  export LLM_PROVIDER=deepseek
  export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-v4-pro}"
  export FORMAL_TAG=r3_gen_ds
elif [[ "$MODE" == "qwen" || "$MODE" == "bailian" ]]; then
  export LLM_PROVIDER=bailian
  export DASHSCOPE_MODEL="${DASHSCOPE_MODEL:-qwen3.8-max}"
  export FORMAL_TAG=r3_gen_qwen
else
  # use whatever .env says
  export FORMAL_TAG=r3_gen
fi
export FORMAL_PROMPTS=P01_generate_table,P10_generate_row
export FORMAL_CONDITIONS=baseline,check
export FORMAL_SEEDS=1
exec "$(dirname "$0")/run_formal_batch.sh"
