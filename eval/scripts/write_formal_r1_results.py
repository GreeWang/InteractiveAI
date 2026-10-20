#!/usr/bin/env python3
"""Write RESULTS_FORMAL_R1.md + CSV from batch_formal_r1_* manifest."""
from __future__ import annotations
import csv, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/InteractiveAI/eval"
runs = eval_dir / "runs"

def pick_batch(arg=None):
    if arg:
        p = Path(arg)
        return p if p.is_absolute() else runs / arg
    last = runs / ".last_formal_r1_batch"
    if last.exists():
        return Path(last.read_text().strip())
    cands = sorted(runs.glob("batch_formal_r1_*"), reverse=True)
    if not cands:
        raise SystemExit("no batch_formal_r1_*")
    return cands[0]

batch = pick_batch(sys.argv[1] if len(sys.argv) > 1 else None)
rows = [json.loads(l) for l in (batch / "manifest.ndjson").read_text().splitlines() if l.strip()]
# stable order
order = []
for pid in ["P02_edit_move_sphere","P03_edit_duplicate_row","P09_edit_raise_sphere",
            "P04_constraint_left_of","P05_constraint_on_top","P06_constraint_distance",
            "P07_constraint_facing","P08_constraint_no_overlap"]:
    for cond in ["baseline","check"]:
        for r in rows:
            if r.get("prompt_id")==pid and r.get("condition")==cond:
                order.append(r)

ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
csv_path = eval_dir / f"results_formal_r1_{ts}.csv"
fields = ["prompt_id","family","condition","seed","model","harness_ok","semantic_or_check_ok","rounds_used","run_dir","notes"]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in order:
        w.writerow({k: r.get(k) for k in fields})

def rate(subset, key="semantic_or_check_ok"):
    if not subset: return "n/a"
    ok = sum(1 for r in subset if r.get(key))
    return f"{ok}/{len(subset)} ({100*ok/len(subset):.0f}%)"

edit_b = [r for r in order if r.get("family")=="edit" and r.get("condition")=="baseline"]
edit_c = [r for r in order if r.get("family")=="edit" and r.get("condition")=="check"]
con_b = [r for r in order if r.get("family")=="constraint" and r.get("condition")=="baseline"]
con_c = [r for r in order if r.get("family")=="constraint" and r.get("condition")=="check"]
all_b = [r for r in order if r.get("condition")=="baseline"]
all_c = [r for r in order if r.get("condition")=="check"]
model = next((r.get("model") for r in order if r.get("model")), "deepseek-v4-pro")
now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

md = eval_dir / "RESULTS_FORMAL_R1.md"
lines = [
    "# Formal Formative Round 1 (minimal)",
    "",
    f"Updated: {now} Asia/Shanghai (UTC+8)",
    f"Batch: `{batch.name}`",
    f"Model: **{model}** only · seeds=**1** per cell · check max_rounds=**3**",
    "Prompts: **P02–P09** (P01/P10 generate deferred).",
    "",
    "## Aggregate success (semantic / ConstraintChecker)",
    "",
    "| Slice | baseline | check (multiturn) |",
    "|---|---|---|",
    f"| Edit (P02/P03/P09) | {rate(edit_b)} | {rate(edit_c)} |",
    f"| Constraint (P04–P08) | {rate(con_b)} | {rate(con_c)} |",
    f"| All | {rate(all_b)} | {rate(all_c)} |",
    "",
    f"Harness OK — baseline {rate(all_b,'harness_ok')} · check {rate(all_c,'harness_ok')}",
    "",
    "## Matrix",
    "",
    "| prompt | condition | harness_ok | semantic/check_ok | rounds | notes |",
    "|---|---|---|---|---|---|",
]
for r in order:
    notes = str(r.get("notes") or "").replace("|","/").replace("\n"," ")[:80]
    lines.append(
        f"| {r.get('prompt_id')} | {r.get('condition')} | "
        f"{'✅' if r.get('harness_ok') else '❌'} | "
        f"{'✅' if r.get('semantic_or_check_ok') else '❌'} | "
        f"{r.get('rounds_used','')} | `{notes}` |"
    )
lines += [
    "",
    f"CSV: `{csv_path.name}`",
    f"Manifest: `{batch}/manifest.ndjson`",
    "",
    "## Protocol notes",
    "",
    "- R1 minimal: DeepSeek only (`deepseek-v4-pro`); no second model family.",
    "- `baseline` = single-shot LLM→CLI; scored by postcheck / ConstraintChecker after execute.",
    "- `check` = multiturn repair up to 3 rounds (`llm_multiturn.py`).",
    "- Fixtures restored between cells; generate prompts P01/P10 deferred.",
    "",
]
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {md}")
print(f"wrote {csv_path}")
print("edit baseline", rate(edit_b), "check", rate(edit_c))
print("constraint baseline", rate(con_b), "check", rate(con_c))
