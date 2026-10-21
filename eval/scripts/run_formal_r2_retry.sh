#!/usr/bin/env bash
# Retry dirty R2 cells: P05 check + P08 check on Bailian qwen3.8-max
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
export LLM_PROVIDER=bailian
export DASHSCOPE_MODEL="${DASHSCOPE_MODEL:-qwen3.8-max}"
export FORMAL_TAG=r2_retry
export FORMAL_PROMPTS=P05_constraint_on_top,P08_constraint_no_overlap
export FORMAL_CONDITIONS=check
export FORMAL_SEEDS=1
exec "$(dirname "$0")/run_formal_batch.sh"
