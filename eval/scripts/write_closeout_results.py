#!/usr/bin/env python3
"""Aggregate closeout batch manifest.ndjson into CSV + markdown."""
from __future__ import annotations
import argparse, csv, json, time
from collections import defaultdict
from pathlib import Path

def load_manifest(batch_dir: Path):
    rows = []
    for line in (batch_dir / "manifest.ndjson").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows

def summarize(rows):
    by = defaultdict(lambda: {"n": 0, "ok": 0, "wall": 0, "tok": 0, "cmds": 0})
    for r in rows:
        k = r["condition"]
        by[k]["n"] += 1
        by[k]["ok"] += 1 if r.get("semantic_ok") else 0
        by[k]["wall"] += int(r.get("wall_ms") or 0)
        by[k]["tok"] += int(r.get("total_tokens") or 0)
        by[k]["cmds"] += int(r.get("n_commands") or 0)
    return by

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()
    batch = Path(args.batch_dir)
    rows = load_manifest(batch)
    by = summarize(rows)
    # CSV
    fields = ["tag","prompt_id","condition","seed","provider","model","fixture","semantic_ok","rounds_used","n_commands","wall_ms","prompt_tokens","completion_tokens","total_tokens","rc","run_dir"]
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    # MD
    lines = [f"# {args.title}", "", f"Updated: {time.strftime('%Y-%m-%dT%H:%M:%S%z')} Asia/Shanghai", "",
             f"Batch: `{batch}`", f"Cells: **{len(rows)}**", ""]
    if args.notes:
        lines += [args.notes, ""]
    lines += ["## Aggregate by condition", "", "| condition | success | rate | mean wall_ms | total tokens | mean cmds |",
              "|-----------|---------|------|--------------|--------------|-----------|"]
    for cond, s in sorted(by.items()):
        rate = s["ok"]/s["n"] if s["n"] else 0
        lines.append(f"| {cond} | {s['ok']}/{s['n']} | {rate:.0%} | {s['wall']//max(s['n'],1)} | {s['tok']} | {s['cmds']/max(s['n'],1):.1f} |")
    lines += ["", "## Per cell", "", "| prompt | cond | seed | ok | rounds | cmds | wall_ms | tokens |",
              "|--------|------|------|----|--------|------|---------|--------|"]
    for r in rows:
        lines.append(
            f"| {r['prompt_id']} | {r['condition']} | {r['seed']} | {'✅' if r.get('semantic_ok') else '❌'} | {r.get('rounds_used')} | {r.get('n_commands')} | {r.get('wall_ms')} | {r.get('total_tokens')} |"
        )
    fails = [r for r in rows if not r.get("semantic_ok")]
    lines += ["", f"## Failures ({len(fails)})", ""]
    if not fails:
        lines.append("None.")
    else:
        for r in fails:
            lines.append(f"- `{r['prompt_id']}` / {r['condition']} / seed={r['seed']}: {(r.get('report') or '')[:180]}")
    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(rows), "by": {k: {"ok": v["ok"], "n": v["n"]} for k,v in by.items()}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
