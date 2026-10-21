#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.unity/bin:${PATH}"
export TZ=Asia/Shanghai
export LLM_PROVIDER=bailian
export DASHSCOPE_MODEL=qwen3.8-max
LOG="$ROOT/runs/all_closeout_nohup.log"
mkdir -p "$ROOT/runs"

run_and_write() {
  local tag="$1" prompts="$2" conds="$3" seeds="$4" pfile="$5" md="$6" csv="$7" title="$8" notes="$9"
  echo "======== START $tag $(date) ========" | tee -a "$LOG"
  FORMAL_TAG="$tag" FORMAL_PROMPTS="$prompts" FORMAL_CONDITIONS="$conds" FORMAL_SEEDS="$seeds" \
    PROMPTS_FILE="$pfile" \
    bash "$ROOT/scripts/run_closeout_batch.sh" >>"$LOG" 2>&1
  BATCH="$(cat "$ROOT/runs/.last_${tag}_batch")"
  python3 "$ROOT/scripts/write_closeout_results.py" \
    --batch-dir "$BATCH" --out-md "$ROOT/$md" --out-csv "$ROOT/$csv" \
    --title "$title" --notes "$notes" | tee -a "$LOG"
  echo "======== DONE $tag $(date) ========" | tee -a "$LOG"
}

MATRIX="P01_generate_table,P02_edit_move_sphere,P03_edit_duplicate_row,P04_constraint_left_of,P05_constraint_on_top,P06_constraint_distance,P07_constraint_facing,P08_constraint_no_overlap,P09_edit_raise_sphere,P10_generate_row,P11_constraint_clearance,P12_constraint_locked"
HELDOUT="H01_gen_desk_mug,H02_edit_sphere_stack,H03_edit_side_cube,H04_left_same_y,H05_cup_stack,H06_spacing_band,H07_face_neighbor,H08_no_penetrate,H09_lift_sphere,H10_row_xyz,H11_keepout,H12_preserve_red"
ABLATION="P02_edit_move_sphere,P05_constraint_on_top,P08_constraint_no_overlap,P11_constraint_clearance,P01_generate_table,P12_constraint_locked"

run_and_write task_matrix "$MATRIX" "baseline,check" "1,2,3" \
  "$ROOT/prompts/prompts.json" \
  "RESULTS_TASK_MATRIX.md" "results_task_matrix.csv" \
  "Results — Scripted Task Matrix (12×3×A/B)" \
  "Model fixed: qwen3.8-max. 12 prompts × seeds 1–3 × baseline/check."

run_and_write heldout_ab "$HELDOUT" "baseline,check" "1,2,3" \
  "$ROOT/prompts/heldout.json" \
  "RESULTS_HELDOUT_AB.md" "results_heldout_ab.csv" \
  "Results — Held-out A/B (12 briefs)" \
  "Shortfall vs proposal 24 briefs: ran **12** held-out × 3 seeds × A/B (72 cells) to control API cost/time. Model fixed: qwen3.8-max."

run_and_write ablation "$ABLATION" "baseline,skill,check" "1" \
  "$ROOT/prompts/prompts.json" \
  "RESULTS_ABLATION.md" "results_ablation.csv" \
  "Results — Skill-only Ablation (6 briefs × 3 arms)" \
  "Arms: baseline (ordinary prompt), skill (richer prompt, no Check loop), check (multiturn ≤3). Seed=1. Model: qwen3.8-max."

echo ALL_CLOSEOUT_COMPLETE | tee -a "$LOG"
