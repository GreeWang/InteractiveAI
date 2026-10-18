#!/usr/bin/env python3
"""Write RESULTS_AB.md and results_ab_*.csv from prompts + newest runs."""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

eval_dir = Path.home() / "Projects/Prompt2Scene/eval"
prompts = json.load(open(eval_dir / "prompts/prompts.json"))["prompts"]
runs_root = eval_dir / "runs"

def parse_run_name(name: str):
    # YYYYMMDD-HHMMSS_<prompt_id>_<condition>
    if len(name) < 16 or name[8] != "-":
        return None, None
    rest = name[16:]
    if rest.endswith("_baseline"):
        return rest[: -len("_baseline")], "baseline"
    if rest.endswith("_check"):
        return rest[: -len("_check")], "check"
    return None, None

runs = [r for r in runs_root.iterdir() if r.is_dir()]
rows = []
for p in prompts:
    pid = p["id"]
    auto = p.get("automation", "none")
    if auto == "none":
        rows.append({
            "prompt_id": pid,
            "phase": p.get("phase"),
            "fixture": p.get("fixture"),
            "condition": "n/a",
            "automation": auto,
            "success": False,
            "status": "not_automated",
            "run_folder": "",
            "passed": "",
            "failed": "",
            "notes": p.get("notes", "LLM generation not wired"),
        })
        continue
    cond = "baseline" if auto == "baseline_cli" else "check"
    best = None
    for r in sorted(runs, key=lambda x: x.name):
        pid2, c2 = parse_run_name(r.name)
        if pid2 == pid and c2 == cond:
            best = r
    status = "missing_run"
    success = False
    passed = failed = ""
    folder = ""
    if best and (best / "result.json").exists():
        folder = str(best)
        res = json.loads((best / "result.json").read_text())
        success = bool(res.get("success"))
        status = "ok" if success else "failed"
        cr = best / "check_report.json"
        if cr.exists():
            rep = json.loads(cr.read_text())
            passed = rep.get("passed", "")
            failed = rep.get("failed", "")
    rows.append({
        "prompt_id": pid,
        "phase": p.get("phase"),
        "fixture": p.get("fixture"),
        "condition": cond,
        "automation": auto,
        "success": success,
        "status": status,
        "run_folder": folder,
        "passed": passed,
        "failed": failed,
        "notes": "; ".join(p.get("success_criteria", [])),
    })

ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
csv_path = eval_dir / f"results_ab_{ts}.csv"
md_path = eval_dir / "RESULTS_AB.md"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

lines = [
    "# Prompt2Scene Formative A/B Results",
    "",
    f"Updated: {datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')} (Asia/Shanghai)",
    "",
    "**Honest scope:** `baseline_cli` = Unity CLI edit smoke (no LLM). "
    "`check_cli` = ConstraintChecker on seeded F03. "
    "`none` = generate prompts not automated yet.",
    "",
    f"CSV: `{csv_path.name}`",
    "",
    "| prompt_id | phase | fixture | condition | automation | success | status | passed/failed | run_folder |",
    "|---|---|---|---|---|---|---|---|---|",
]
for r in rows:
    pf = f"{r['passed']}/{r['failed']}" if r["passed"] != "" else ""
    folder = r["run_folder"].replace(str(Path.home()), "~") if r["run_folder"] else ""
    lines.append(
        f"| {r['prompt_id']} | {r['phase']} | {r['fixture']} | {r['condition']} | "
        f"{r['automation']} | {r['success']} | {r['status']} | {pf} | `{folder}` |"
    )
lines += [
    "",
    "## Counts",
    f"- Prompts total: {len(rows)}",
    f"- Automated success: {sum(1 for r in rows if r['success'])}",
    f"- Failed: {sum(1 for r in rows if r['status'] == 'failed')}",
    f"- Not automated: {sum(1 for r in rows if r['status'] == 'not_automated')}",
    f"- Missing run: {sum(1 for r in rows if r['status'] == 'missing_run')}",
]
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", csv_path)
print("wrote", md_path)
