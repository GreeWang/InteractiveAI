#!/usr/bin/env python3
"""Write RESULTS_LLM.md + results_llm_*.csv from a batch_llm_* manifest."""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/InteractiveAI/eval"
runs = eval_dir / "runs"

def pick_batch(arg: str | None) -> Path:
    if arg:
        p = Path(arg)
        if not p.is_absolute():
            p = runs / arg
        return p
    last = runs / ".last_llm_batch"
    if last.exists():
        return Path(last.read_text().strip())
    cands = sorted(runs.glob("batch_llm_*"), reverse=True)
    if not cands:
        raise SystemExit("no batch_llm_* found")
    return cands[0]

batch = pick_batch(sys.argv[1] if len(sys.argv) > 1 else None)
manifest = batch / "manifest.ndjson"
if not manifest.exists():
    raise SystemExit(f"missing {manifest}")

rows = []
for line in manifest.read_text().splitlines():
    if line.strip():
        rows.append(json.loads(line))

# Enrich from run files if needed
for r in rows:
    rd = Path(r.get("run_dir") or "")
    if rd.is_dir():
        meta_p = rd / "meta.json"
        if meta_p.exists():
            meta = json.load(open(meta_p))
            r["model"] = meta.get("model")
            r["started_at"] = meta.get("started_at")
            r["ended_at"] = meta.get("ended_at")
        if (rd / "llm_response.json").exists():
            resp = json.load(open(rd / "llm_response.json"))
            r["model"] = r.get("model") or resp.get("model")
            r["usage"] = resp.get("usage")

ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
csv_path = eval_dir / f"results_llm_{ts}.csv"
md_path = eval_dir / "RESULTS_LLM.md"

fields = [
    "prompt_id", "condition", "model", "harness_success", "semantic_pass",
    "check_success", "check_passed", "check_failed", "n_commands",
    "llm_run_exit", "postcheck", "run_dir", "started_at", "ended_at",
]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        row = {k: r.get(k) for k in fields}
        if isinstance(row.get("postcheck"), (dict, list)):
            row["postcheck"] = json.dumps(row["postcheck"], ensure_ascii=False)
        w.writerow(row)

n = len(rows)
n_h = sum(1 for r in rows if r.get("harness_success"))
n_s = sum(1 for r in rows if r.get("semantic_pass"))
n_c = sum(1 for r in rows if r.get("condition") == "check")
n_c_ok = sum(1 for r in rows if r.get("condition") == "check" and r.get("check_success"))
n_e = sum(1 for r in rows if r.get("condition") == "baseline")
n_e_ok = sum(1 for r in rows if r.get("condition") == "baseline" and r.get("semantic_pass"))
model = next((r.get("model") for r in rows if r.get("model")), "deepseek-v4-pro")
now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

lines = [
    "# Prompt2Scene LLM Formative Batch Results",
    "",
    f"Updated: {now} Asia/Shanghai (UTC+8)",
    f"Batch: `{batch.name}`",
    f"Model: **{model}**",
    "",
    "This table is for **LLM → Unity CLI** runs (`llm_run.sh`), distinct from the earlier CLI-only A/B (`RESULTS_AB.md`).",
    "",
    "## Summary",
    "",
    f"| Metric | Count |",
    f"|---|---|",
    f"| Prompts ran | {n} |",
    f"| Harness success (commands/API) | {n_h}/{n} |",
    f"| Semantic / Check pass | {n_s}/{n} |",
    f"| Edit baseline semantic pass | {n_e_ok}/{n_e} |",
    f"| Constraint check pass | {n_c_ok}/{n_c} |",
    "",
    "## Per-prompt",
    "",
    "| prompt_id | condition | harness | semantic/check | n_cmds | notes |",
    "|---|---|---|---|---|---|",
]
for r in rows:
    note = ""
    if r.get("condition") == "check":
        note = f"check failed={r.get('check_failed')} passed={r.get('check_passed')}"
        flag = "✅" if r.get("check_success") else "❌"
        sem = flag
    else:
        note = str(r.get("postcheck") or r.get("semantic_note") or "")[:80]
        sem = "✅" if r.get("semantic_pass") else "❌"
    har = "✅" if r.get("harness_success") else "❌"
    lines.append(
        f"| {r.get('prompt_id')} | {r.get('condition')} | {har} | {sem} | {r.get('n_commands','')} | {note} |"
    )

lines += [
    "",
    f"CSV: `{csv_path.name}`",
    f"Manifest: `{batch}/manifest.ndjson`",
    "",
    "## Notes",
    "",
    "- **Harness success**: DeepSeek returned a valid plan and Unity CLI steps reported success (or check path completed).",
    "- **Semantic pass (edit)**: post-edit scene query matched prompt criteria before fixture restore.",
    "- **Check pass (constraint)**: `ConstraintChecker` report `success=true` after LLM edits (seeded F03 may already satisfy).",
    "- Fixtures F02/F03 were restored after each prompt in the batch script.",
    "",
]
md_path.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {md_path}")
print(f"wrote {csv_path}")
print(f"summary harness={n_h}/{n} semantic={n_s}/{n}")
