#!/usr/bin/env python3
"""Aggregate R1/R2 seed=1 + multiseed_ds/qwen seeds 2,3 into RESULTS_FORMAL_MULTISEED.md."""
from __future__ import annotations
import csv, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/InteractiveAI/eval"
runs = eval_dir / "runs"
tz = ZoneInfo("Asia/Shanghai")
now = datetime.now(tz).isoformat(timespec="seconds")

def load_manifest(path: Path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

def pick_dir(pattern: str, exclude_substr=None):
    cands = [p for p in sorted(runs.glob(pattern), reverse=True) if p.is_dir()]
    if exclude_substr:
        cands = [p for p in cands if exclude_substr not in p.name]
    return cands[0] if cands else None

rows = []
# R1 seed 1 DS
r1 = pick_dir("batch_formal_r1_*")
if r1:
    for r in load_manifest(r1 / "manifest.ndjson"):
        r.setdefault("provider", "deepseek")
        r.setdefault("model", "deepseek-v4-pro")
        r.setdefault("seed", 1)
        r["source_batch"] = r1.name
        rows.append(r)
# R2 seed 1 Qwen — use patched CSV if present else original + note
r2 = pick_dir("batch_formal_r2_*", exclude_substr="retry")
if r2:
    for r in load_manifest(r2 / "manifest.ndjson"):
        r.setdefault("provider", "bailian")
        r.setdefault("model", "qwen3.8-max")
        r.setdefault("seed", 1)
        r["source_batch"] = r2.name
        rows.append(r)
# Prefer retry overlay for P05/P08 check
retry = pick_dir("batch_formal_r2_retry_*")
if retry:
    by = {(r.get("prompt_id"), r.get("condition"), r.get("seed", 1), r.get("model")): i for i, r in enumerate(rows)}
    for r in load_manifest(retry / "manifest.ndjson"):
        r.setdefault("provider", "bailian")
        r.setdefault("model", "qwen3.8-max")
        key = (r.get("prompt_id"), r.get("condition"), r.get("seed", 1), r.get("model"))
        r["source_batch"] = retry.name
        r["retried"] = True
        if key in by:
            rows[by[key]] = r
        else:
            rows.append(r)
# Multiseed batches
for tag in ("multiseed_ds", "multiseed_qwen"):
    last = runs / f".last_formal_{tag}_batch"
    b = Path(last.read_text().strip()) if last.exists() else pick_dir(f"batch_formal_{tag}_*")
    if not b:
        continue
    for r in load_manifest(b / "manifest.ndjson"):
        r["source_batch"] = b.name
        rows.append(r)

# Also merge post-harden P05 baseline smokes for qwen/ds seed1 if still failing
# (optional — leave matrix as formal batches)

def rate(subset, key="semantic_or_check_ok"):
    if not subset:
        return "n/a"
    ok = sum(1 for r in subset if r.get(key))
    return f"{ok}/{len(subset)} ({100 * ok / len(subset):.0f}%)"

models = sorted({(r.get("provider"), r.get("model")) for r in rows})
seeds = sorted({r.get("seed", 1) for r in rows})

ts = datetime.now(tz).strftime("%Y%m%d-%H%M%S")
csv_path = eval_dir / f"results_formal_multiseed_{ts}.csv"
fields = ["provider","model","seed","prompt_id","family","condition","harness_ok","semantic_or_check_ok","rounds_used","source_batch","notes"]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in fields})

md = eval_dir / "RESULTS_FORMAL_MULTISEED.md"
lines = [
    "# Formal multi-seed summary (P02–P09)",
    "",
    f"Updated: {now} Asia/Shanghai (UTC+8)",
    f"Seeds present: **{seeds}** · models: {models}",
    "Seed 1 reused from R1 (DeepSeek) / R2 (Qwen, with dirty-cell retry). Seeds 2–3 from `run_formal_multiseed.sh`.",
    "",
    "## Pooled rates",
    "",
]
for prov, model in models:
    sub = [r for r in rows if r.get("provider")==prov or r.get("model")==model]
    # prefer model match
    sub = [r for r in rows if r.get("model")==model]
    b = [r for r in sub if r.get("condition")=="baseline"]
    c = [r for r in sub if r.get("condition")=="check"]
    lines.append(f"- **{model}**: baseline {rate(b)} · check {rate(c)} · n={len(sub)}")

lines += ["", "## Per seed × model", ""]
for seed in seeds:
    for prov, model in models:
        sub = [r for r in rows if r.get("seed",1)==seed and r.get("model")==model]
        if not sub:
            continue
        b = [r for r in sub if r.get("condition")=="baseline"]
        c = [r for r in sub if r.get("condition")=="check"]
        lines.append(f"- seed={seed} · {model}: baseline {rate(b)} · check {rate(c)}")

lines += [
    "",
    "## Matrix (compact failures)",
    "",
    "| model | seed | prompt | condition | ok | notes |",
    "|---|---|---|---|---|---|",
]
fails = [r for r in rows if not r.get("semantic_or_check_ok")]
show = fails if fails else rows[:0]
for r in sorted(rows, key=lambda x: (x.get("model") or "", x.get("seed",1), x.get("prompt_id") or "", x.get("condition") or "")):
    if r.get("semantic_or_check_ok") and fails:
        continue  # only list failures when any exist; else skip huge table
for r in (fails or []):
    notes = str(r.get("notes") or "").replace("|","/")[:60]
    lines.append(
        f"| {r.get('model')} | {r.get('seed')} | {r.get('prompt_id')} | {r.get('condition')} | ❌ | `{notes}` |"
    )
if not fails:
    lines.append("| — | — | — | — | ✅ | all cells in aggregate passed semantic/check |")

lines += ["", f"CSV: `{csv_path.name}`", f"Rows: {len(rows)}", ""]
# full matrix appendix
lines += ["## Full matrix", "", "| model | seed | prompt | condition | ok | rounds |", "|---|---|---|---|---|---|"]
order_p = ["P02_edit_move_sphere","P03_edit_duplicate_row","P09_edit_raise_sphere",
           "P04_constraint_left_of","P05_constraint_on_top","P06_constraint_distance",
           "P07_constraint_facing","P08_constraint_no_overlap"]
for model in sorted({r.get("model") for r in rows}):
    for seed in seeds:
        for pid in order_p:
            for cond in ("baseline","check"):
                match = [r for r in rows if r.get("model")==model and r.get("seed",1)==seed and r.get("prompt_id")==pid and r.get("condition")==cond]
                if not match:
                    continue
                r = match[-1]
                lines.append(
                    f"| {model} | {seed} | {pid} | {cond} | "
                    f"{'✅' if r.get('semantic_or_check_ok') else '❌'} | {r.get('rounds_used','')} |"
                )
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", md)
print("csv", csv_path)
print("rows", len(rows), "fails", len(fails))
