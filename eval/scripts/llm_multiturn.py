#!/usr/bin/env python3
"""Multi-turn LLM repair loop for Prompt2Scene check condition.

Round: plan → execute Unity CLI → verify (ConstraintChecker or edit postcheck).
On failure, feed report back to the model for up to max_rounds.
Never prints API keys.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Reuse client helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_client as lc  # noqa: E402

TZ = ZoneInfo("Asia/Shanghai")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def unity(proj: str, *args: str, result_only: bool = False) -> dict:
    cmd = ["unity", "command", "--project-path", proj, "--format", "json"]
    if result_only:
        cmd.append("--result-only")
    # split command name vs flags: args like ("set_transform", "--", "--target", ...)
    cmd.extend(args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout or ""
    try:
        data = json.loads(out) if out.strip().startswith("{") else {"raw": out, "success": p.returncode == 0}
    except json.JSONDecodeError:
        data = {"raw": out[:4000], "success": p.returncode == 0}
    data["_exit"] = p.returncode
    data["_stderr"] = (p.stderr or "")[:2000]
    if "success" not in data:
        data["success"] = p.returncode == 0
    return data


def eval_code(proj: str, code: str) -> str:
    data = unity(proj, "eval", "--", "--code", code, result_only=True)
    if isinstance(data.get("result"), str):
        return data["result"]
    if isinstance(data.get("raw"), str):
        return data["raw"]
    return json.dumps(data, ensure_ascii=False)


def open_scene(proj: str, scene: str) -> None:
    unity(proj, "open_scene", "--", "--path", scene)


def execute_plan(proj: str, plan: dict, run_dir: Path, round_i: int, ndjson: Path) -> list[str]:
    errors: list[str] = []
    round_dir = run_dir / f"round_{round_i:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cmds_log = []
    for c in plan.get("commands") or []:
        name = c.get("command") or c.get("cmd")
        if not name or name == "open_scene":
            continue
        # Skip save_scene during intermediate repair? Allow save; restore is external.
        label = c.get("label") or name
        argv = ["unity", "command", "--project-path", proj, "--format", "json", name, "--"] + list(c.get("args") or [])
        t0 = time.time()
        p = subprocess.run(argv, capture_output=True, text=True)
        dur = int((time.time() - t0) * 1000)
        out, err = p.stdout or "", p.stderr or ""
        success = p.returncode == 0 and '"success": false' not in out and '"success":false' not in out
        rec = {
            "ts": now_iso(),
            "round": round_i,
            "label": label,
            "argv": argv,
            "exit_code": p.returncode,
            "duration_ms": dur,
            "success": success,
            "stdout_snip": out[:2000],
        }
        with ndjson.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        cmds_log.append(rec)
        print(f"[multiturn] r{round_i} {label}: success={success} exit={p.returncode} {dur}ms")
        if not success:
            errors.append(label)
    (round_dir / "exec.json").write_text(json.dumps({"errors": errors, "commands": cmds_log}, indent=2, ensure_ascii=False) + "\n")
    return errors


def verify_edit(proj: str, prompt_id: str) -> dict:
    """Semantic postcheck for edit prompts (used as check signal)."""
    if prompt_id.startswith("P02"):
        code = (
            'var a=GameObject.Find("CubeA").transform.position;'
            'var b=GameObject.Find("SphereB").transform.position;'
            'var above=(b.y>a.y+0.4f)&&(Mathf.Abs(b.x-a.x)<0.6f)&&(Mathf.Abs(b.z-a.z)<0.6f);'
            'return "pass="+above+";SphereB="+b+";CubeA="+a+";detail=SphereB_above_CubeA";'
        )
    elif prompt_id.startswith("P03"):
        code = (
            'var c=GameObject.Find("CubeC");'
            'if(c==null) return "pass=False;exists=False;dist=-1;detail=CubeC_missing";'
            'var a=GameObject.Find("CubeA").transform.position;'
            'var d=Vector3.Distance(a,c.transform.position);'
            'var ok=(d>=1.2f && d<=1.8f);'
            'return "pass="+ok+";exists=True;dist="+d+";detail=CubeC_spacing";'
        )
    elif prompt_id.startswith("P09"):
        code = (
            'var b=GameObject.Find("SphereB").transform.position;'
            'var ok=Mathf.Abs(b.y-2.0f)<0.15f;'
            'var xz_ok=Mathf.Abs(b.x-1.5f)<0.05f && Mathf.Abs(b.z-0f)<0.05f;'
            # xz seed is 1.5,0 — require y≈2; xz preferably unchanged
            'return "pass="+ok+";y="+b.y+";xz_ok="+xz_ok+";SphereB="+b+";detail=SphereB_y_approx_2";'
        )
    else:
        return {"pass": False, "report": f"no_edit_verifier_for:{prompt_id}", "kind": "edit_postcheck"}
    raw = eval_code(proj, code)
    passed = "pass=True" in raw or "pass=true" in raw
    return {"pass": passed, "report": raw, "kind": "edit_postcheck"}


def verify_constraint(proj: str, constraint_file: str, run_dir: Path, round_i: int) -> dict:
    abs_path = str(Path(proj) / constraint_file)
    code = (
        f'var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@"{abs_path}");'
        'return "success="+r.success+" passed="+r.passed+" failed="+r.failed+" skipped="+r.skipped+" set="+r.set_id;'
    )
    raw = eval_code(proj, code)
    report_src = Path(proj) / "Logs/prompt2scene-check-last.json"
    report = {}
    if report_src.is_file():
        b = report_src.read_bytes()
        if b.startswith(b"\xef\xbb\xbf"):
            b = b[3:]
        report = json.loads(b.decode("utf-8"))
        dest = run_dir / f"round_{round_i:02d}" / "check_report.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    passed = bool(report.get("success")) if report else ("success=True" in raw)
    # Build failure detail for LLM
    fails = []
    for c in report.get("constraints") or report.get("results") or []:
        if not isinstance(c, dict):
            continue
        if c.get("success") is False or c.get("passed") is False:
            fails.append(c)
    detail = {
        "eval_snip": raw,
        "failed_constraints": fails or report.get("failures") or [],
        "passed": report.get("passed"),
        "failed": report.get("failed"),
    }
    return {"pass": passed, "report": json.dumps(detail, ensure_ascii=False), "kind": "constraint", "raw_report": report}


def verify(proj: str, prompt: dict, run_dir: Path, round_i: int) -> dict:
    pid = prompt["id"]
    fixture = prompt.get("fixture") or ""
    cfile = prompt.get("constraint_file") or ""
    if fixture == "F03" and cfile:
        return verify_constraint(proj, cfile, run_dir, round_i)
    if pid.startswith(("P02", "P03", "P09")):
        return verify_edit(proj, pid)
    return {"pass": False, "report": "unsupported_prompt_for_check", "kind": "none"}


REPAIR_SYSTEM_EXTRA = """
Repair mode extras:
- You are fixing a FAILED check. Read the failure report carefully and emit a MINIMAL repair plan.
- Do NOT undo correct work. Do NOT restore objects to their pre-task poses unless the task asks to restore.
- For raise/move tasks: leave the object at the target pose; never add a restore step.
- For spacing: distance between CubeA and CubeC must be about 1.5 (acceptable 1.2–1.8). If CubeA is at (0,0.5,0), place CubeC near (1.5,0.5,0).
- Prefer set_transform / create_gameobject / delete_gameobject only as needed.
"""


def ask_plan(task: str, scene: str, fixture: str, extra: str, out_path: Path, temperature: float = 0.2) -> dict:
    system = lc.SYSTEM_PROMPT + ("\n" + REPAIR_SYSTEM_EXTRA if extra else "")
    user = lc.build_user_prompt(task, scene, fixture, extra)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    result = lc.chat(messages, temperature=temperature)
    # redact key defensively
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    text = json.dumps(result, ensure_ascii=False)
    if key and key in text:
        text = text.replace(key, "<redacted>")
        result = json.loads(text)
    try:
        plan = lc.normalize_plan(lc.extract_json_object(result["content"]))
        result["plan"] = plan
        result["plan_ok"] = True
    except Exception as e:
        result["plan_ok"] = False
        result["plan_error"] = str(e)
        result["plan"] = {"commands": [], "notes": ""}
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def build_task(prompt: dict) -> str:
    zh = prompt.get("text_zh") or ""
    en = prompt.get("text_en") or ""
    criteria = prompt.get("success_criteria") or []
    parts = [zh, en]
    if criteria:
        parts.append("Success criteria:\n- " + "\n- ".join(criteria))
    parts.append(
        "Important: do not revert/restore the scene after applying the edit unless the user explicitly asks."
    )
    return "\n\n".join(p for p in parts if p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dotenv", default="")
    ap.add_argument("--prompt-json", required=True, help="Single prompt object JSON file or inline path")
    ap.add_argument("--project", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dotenv:
        lc.load_dotenv(args.dotenv)

    prompt = json.loads(Path(args.prompt_json).read_text(encoding="utf-8"))
    proj = args.project
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ndjson = run_dir / "commands.ndjson"
    ndjson.write_text("", encoding="utf-8")

    scene = prompt.get("scene") or ""
    fixture = prompt.get("fixture") or ""
    task = build_task(prompt)
    max_rounds = max(1, args.max_rounds)

    rounds_meta = []
    final_pass = False
    last_report = ""

    if not args.dry_run:
        # pipeline ping
        st = subprocess.run(["unity", "status", "--json"], capture_output=True, text=True)
        if st.returncode != 0 or '"ready"' not in (st.stdout or ""):
            print(json.dumps({"ok": False, "error": "unity_pipeline_not_ready"}))
            return 2
        open_scene(proj, scene)

    extra = ""
    for i in range(1, max_rounds + 1):
        round_dir = run_dir / f"round_{i:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        print(f"[multiturn] === round {i}/{max_rounds} ===")
        if extra:
            (round_dir / "failure_feedback.txt").write_text(extra, encoding="utf-8")

        try:
            llm_res = ask_plan(task, scene, fixture, extra, round_dir / "llm_response.json")
        except Exception as e:
            rounds_meta.append({"round": i, "plan_ok": False, "error": str(e)})
            last_report = f"llm_error:{e}"
            break

        if not llm_res.get("plan_ok"):
            rounds_meta.append({"round": i, "plan_ok": False, "error": llm_res.get("plan_error")})
            last_report = f"plan_error:{llm_res.get('plan_error')}"
            extra = (
                f"Previous output was invalid JSON plan: {llm_res.get('plan_error')}\n"
                f"Raw content (truncated):\n{(llm_res.get('content') or '')[:1500]}\n"
                "Emit a valid commands JSON object."
            )
            continue

        plan = llm_res["plan"]
        (round_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")

        if args.dry_run:
            ver = {"pass": False, "report": "dry_run_skip_verify", "kind": "dry"}
            exec_errors = []
        else:
            exec_errors = execute_plan(proj, plan, run_dir, i, ndjson)
            ver = verify(proj, prompt, run_dir, i)

        (round_dir / "verify.json").write_text(json.dumps(ver, indent=2, ensure_ascii=False) + "\n")
        rec = {
            "round": i,
            "plan_ok": True,
            "n_commands": len(plan.get("commands") or []),
            "exec_errors": exec_errors,
            "verify_pass": ver.get("pass"),
            "verify_kind": ver.get("kind"),
            "verify_report": ver.get("report"),
        }
        rounds_meta.append(rec)
        last_report = str(ver.get("report") or "")
        print(f"[multiturn] verify pass={ver.get('pass')} report={last_report[:200]}")

        if ver.get("pass"):
            final_pass = True
            break

        extra = (
            f"Round {i} FAILED verification ({ver.get('kind')}).\n"
            f"Failure report:\n{last_report}\n"
            f"Exec errors: {exec_errors}\n"
            f"Success criteria: {prompt.get('success_criteria')}\n"
            "Emit a repair plan that fixes ONLY what failed. "
            "Do not restore/revert the intended edit."
        )

    summary = {
        "ok": final_pass,
        "prompt_id": prompt.get("id"),
        "max_rounds": max_rounds,
        "rounds_used": len(rounds_meta),
        "final_pass": final_pass,
        "last_report": last_report,
        "rounds": rounds_meta,
        "ended_at": now_iso(),
    }
    (run_dir / "multiturn_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    # convenience copies of last plan
    if rounds_meta:
        last_round = run_dir / f"round_{len(rounds_meta):02d}"
        if (last_round / "plan.json").exists():
            (run_dir / "plan.json").write_text((last_round / "plan.json").read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"final_pass": final_pass, "rounds_used": len(rounds_meta)}, ensure_ascii=False))
    return 0 if final_pass else 1


if __name__ == "__main__":
    sys.exit(main())
