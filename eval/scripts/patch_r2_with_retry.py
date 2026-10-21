#!/usr/bin/env python3
"""Merge r2_retry manifest into RESULTS_FORMAL_R2.md and append retry audit."""
from __future__ import annotations
import csv, json, shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/InteractiveAI/eval"
runs = eval_dir / "runs"
tz = ZoneInfo("Asia/Shanghai")
now = datetime.now(tz).isoformat(timespec="seconds")

retry_last = runs / ".last_formal_r2_retry_batch"
if not retry_last.exists():
    raise SystemExit("no r2_retry batch")
retry_batch = Path(retry_last.read_text().strip())
retry_rows = [json.loads(l) for l in (retry_batch / "manifest.ndjson").read_text().splitlines() if l.strip()]

# Original R2 batch
r2_last = runs / ".last_formal_r2_batch"
r2_batch = Path(r2_last.read_text().strip()) if r2_last.exists() else sorted(runs.glob("batch_formal_r2_2*"), reverse=True)[0]
# Prefer the original non-retry batch
cands = [p for p in sorted(runs.glob("batch_formal_r2_*"), reverse=True)
         if p.is_dir() and "retry" not in p.name]
if not cands:
    raise SystemExit("no original batch_formal_r2_* dir")
r2_batch = cands[0]
rows = [json.loads(l) for l in (r2_batch / "manifest.ndjson").read_text().splitlines() if l.strip()]

audit = []
by_key = {(r.get("prompt_id"), r.get("condition"), r.get("seed", 1)): r for r in rows}
for rr in retry_rows:
    key = (rr.get("prompt_id"), rr.get("condition"), rr.get("seed", 1))
    old = by_key.get(key)
    audit.append({
        "prompt_id": key[0],
        "condition": key[1],
        "seed": key[2],
        "before_sem": None if not old else old.get("semantic_or_check_ok"),
        "before_notes": None if not old else (old.get("notes") or "")[:200],
        "after_sem": rr.get("semantic_or_check_ok"),
        "after_notes": (rr.get("notes") or "")[:200],
        "retry_run_dir": rr.get("run_dir"),
    })
    # replace
    by_key[key] = {**old, **rr, "retried": True, "retry_batch": str(retry_batch)} if old else {**rr, "retried": True}

order_ids = ["P02_edit_move_sphere","P03_edit_duplicate_row","P09_edit_raise_sphere",
             "P04_constraint_left_of","P05_constraint_on_top","P06_constraint_distance",
             "P07_constraint_facing","P08_constraint_no_overlap"]
order = []
for pid in order_ids:
    for cond in ["baseline","check"]:
        k = (pid, cond, 1)
        if k in by_key:
            order.append(by_key[k])

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
model = next((r.get("model") for r in order if r.get("model")), "qwen3.8-max")

ts = datetime.now(tz).strftime("%Y%m%d-%H%M%S")
csv_path = eval_dir / f"results_formal_r2_{ts}.csv"
fields = ["prompt_id","family","condition","seed","model","harness_ok","semantic_or_check_ok","rounds_used","run_dir","notes","retried"]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in order:
        w.writerow({k: r.get(k) for k in fields})

audit_path = retry_batch / "retry_audit.json"
audit_path.write_text(json.dumps({"updated": now, "original_batch": str(r2_batch), "retries": audit}, indent=2, ensure_ascii=False) + "\n")

md = eval_dir / "RESULTS_FORMAL_R2.md"
lines = [
    "# Formal Formative Round 2 (Bailian / Qwen)",
    "",
    f"Updated: {now} Asia/Shanghai (UTC+8) — **includes dirty-cell retries**",
    f"Original batch: `{r2_batch.name}`",
    f"Retry batch: `{retry_batch.name}`",
    f"Model: **{model}** · seeds=**1** · check max_rounds=**3**",
    "Prompts: **P02–P09** (generate → see R3).",
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
    "| prompt | condition | harness_ok | semantic/check_ok | rounds | retried | notes |",
    "|---|---|---|---|---|---|---|",
]
for r in order:
    notes = str(r.get("notes") or "").replace("|","/").replace("\n"," ")[:80]
    lines.append(
        f"| {r.get('prompt_id')} | {r.get('condition')} | "
        f"{'✅' if r.get('harness_ok') else '❌'} | "
        f"{'✅' if r.get('semantic_or_check_ok') else '❌'} | "
        f"{r.get('rounds_used','')} | {'yes' if r.get('retried') else ''} | `{notes}` |"
    )
lines += ["", "## Retry audit", ""]
for a in audit:
    lines.append(
        f"- **{a['prompt_id']} {a['condition']}**: before={a['before_sem']} → after={a['after_sem']}"
    )
    lines.append(f"  - before notes: `{a['before_notes']}`")
    lines.append(f"  - after notes: `{a['after_notes']}`")
lines += [
    "",
    f"CSV: `{csv_path.name}`",
    f"Retry audit JSON: `{audit_path}`",
    "",
    "## Protocol notes",
    "",
    "- R2: Bailian/DashScope `qwen3.8-max`.",
    "- Dirty cells (API timeout / disconnect) retried after P05 prompt harden.",
    "- P05 cells now prep CupOnBox to `[0,0.5,0]` so on_top is a real placement task.",
    "",
]
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("updated", md)
print("csv", csv_path)
print("audit", audit_path)
for a in audit:
    print(a["prompt_id"], a["condition"], a["before_sem"], "->", a["after_sem"])
