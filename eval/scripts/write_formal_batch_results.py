#!/usr/bin/env python3
"""Write RESULTS_FORMAL_<TAG>.md + CSV from batch_formal_<tag>_* manifest."""
from __future__ import annotations
import csv, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/InteractiveAI/eval"
runs = eval_dir / "runs"

def pick_batch(tag: str, arg=None):
    if arg:
        p = Path(arg)
        return p if p.is_absolute() else runs / arg
    last = runs / f".last_formal_{tag}_batch"
    if last.exists():
        return Path(last.read_text().strip())
    cands = sorted(runs.glob(f"batch_formal_{tag}_*"), reverse=True)
    if not cands:
        raise SystemExit(f"no batch_formal_{tag}_*")
    return cands[0]

tag = sys.argv[1] if len(sys.argv) > 1 else "batch"
batch_arg = sys.argv[2] if len(sys.argv) > 2 else None
batch = pick_batch(tag, batch_arg)
rows = [json.loads(l) for l in (batch / "manifest.ndjson").read_text().splitlines() if l.strip()]

# stable-ish order
pref = ["P01_generate_table","P02_edit_move_sphere","P03_edit_duplicate_row","P09_edit_raise_sphere",
        "P04_constraint_left_of","P05_constraint_on_top","P06_constraint_distance",
        "P07_constraint_facing","P08_constraint_no_overlap","P10_generate_row"]
order = []
seeds = sorted({r.get("seed", 1) for r in rows})
conds = ["baseline", "check"]
for seed in seeds:
    for pid in pref:
        for cond in conds:
            for r in rows:
                if r.get("prompt_id")==pid and r.get("condition")==cond and r.get("seed",1)==seed:
                    order.append(r)
# leftovers
seen = {(r.get("prompt_id"), r.get("condition"), r.get("seed")) for r in order}
for r in rows:
    key = (r.get("prompt_id"), r.get("condition"), r.get("seed"))
    if key not in seen:
        order.append(r); seen.add(key)

ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
safe_tag = tag.replace("/", "_")
csv_path = eval_dir / f"results_formal_{safe_tag}_{ts}.csv"
fields = ["prompt_id","family","condition","seed","provider","model","harness_ok","semantic_or_check_ok","rounds_used","run_dir","notes","tag"]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in order:
        w.writerow({k: r.get(k) for k in fields})

def rate(subset, key="semantic_or_check_ok"):
    if not subset: return "n/a"
    ok = sum(1 for r in subset if r.get(key))
    return f"{ok}/{len(subset)} ({100*ok/len(subset):.0f}%)"

model = next((r.get("model") for r in order if r.get("model")), "?")
provider = next((r.get("provider") for r in order if r.get("provider")), "?")
now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

md = eval_dir / f"RESULTS_FORMAL_{safe_tag.upper()}.md"
lines = [
    f"# Formal Formative — {tag}",
    "",
    f"Updated: {now} Asia/Shanghai (UTC+8)",
    f"Batch: `{batch.name}`",
    f"Provider/Model: **{provider} / {model}** · seeds=**{seeds}** · check max_rounds=**3**",
    "",
    "## Aggregate success (semantic / ConstraintChecker)",
    "",
]
for family in ["edit", "constraint", "generate"]:
    b = [r for r in order if r.get("family")==family and r.get("condition")=="baseline"]
    c = [r for r in order if r.get("family")==family and r.get("condition")=="check"]
    if b or c:
        lines.append(f"- **{family}**: baseline {rate(b)} · check {rate(c)}")
all_b = [r for r in order if r.get("condition")=="baseline"]
all_c = [r for r in order if r.get("condition")=="check"]
lines += [
    f"- **all**: baseline {rate(all_b)} · check {rate(all_c)}",
    "",
    "## Per-seed",
    "",
]
for seed in seeds:
    sb = [r for r in order if r.get("seed")==seed and r.get("condition")=="baseline"]
    sc = [r for r in order if r.get("seed")==seed and r.get("condition")=="check"]
    lines.append(f"- seed={seed}: baseline {rate(sb)} · check {rate(sc)}")

lines += [
    "",
    "## Matrix",
    "",
    "| seed | prompt | condition | harness_ok | semantic/check_ok | rounds | notes |",
    "|---|---|---|---|---|---|---|",
]
for r in order:
    notes = str(r.get("notes") or "").replace("|","/").replace("\n"," ")[:80]
    lines.append(
        f"| {r.get('seed')} | {r.get('prompt_id')} | {r.get('condition')} | "
        f"{'✅' if r.get('harness_ok') else '❌'} | "
        f"{'✅' if r.get('semantic_or_check_ok') else '❌'} | "
        f"{r.get('rounds_used','')} | `{notes}` |"
    )
lines += ["", f"CSV: `{csv_path.name}`", f"Manifest: `{batch}/manifest.ndjson`", ""]
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {md}")
print(f"wrote {csv_path}")
print("all baseline", rate(all_b), "check", rate(all_c))
