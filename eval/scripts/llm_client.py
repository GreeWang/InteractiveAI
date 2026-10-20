#!/usr/bin/env python3
"""Minimal OpenAI-compatible DeepSeek chat client for Prompt2Scene eval.

Reads DEEPSEEK_API_KEY from the environment (or eval/.env via llm_run.sh).
Never prints the key. Stdout is JSON only for machine consumption.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"

# Allowed Unity CLI verbs the model may emit (official Pipeline commands).
ALLOWED_COMMANDS = [
    "open_scene",
    "save_scene",
    "find_gameobjects",
    "create_gameobject",
    "delete_gameobject",
    "set_transform",
    "get_component_properties",
    "eval",
]

SYSTEM_PROMPT = """You are a Unity scene editor agent for Prompt2Scene.
Output ONLY a JSON object (no markdown fences) with this shape:
{
  "commands": [
    {"label": "short_step_name", "command": "set_transform", "args": ["--target", "/SphereB", "--position", "[0,1.5,0]"]}
  ],
  "notes": "optional short note"
}

Rules:
- Use ONLY these command names: open_scene, save_scene, find_gameobjects, create_gameobject, delete_gameobject, set_transform, get_component_properties, eval.
- args is a JSON array of CLI flags/values AFTER the command name (same style as Unity Pipeline CLI after `--`).
- Prefer scene-relative targets like /SphereB, /CubeA.
- Positions are Unity world coords as strings like "[x,y,z]".
- For get_component_properties use --type Transform (not --component).
- For create_gameobject use --name X --primitive cube|sphere|capsule|cylinder|plane.
- For set_transform typical: --target /Name --position "[x,y,z]" (optional --rotation / --scale).
- Do not invent packages, MCP tools, or non-listed commands.
- Keep plans short (typically 1–8 commands). open_scene/save_scene may be omitted; the harness can open the scene.
- If the task is ambiguous, pick a simple reasonable plan and explain in notes.
"""


def load_dotenv(path: str) -> None:
    p = os.path.expanduser(path)
    if not os.path.isfile(p):
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip("'").strip('"')
            if k and k not in os.environ:
                os.environ[k] = v


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    base = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE).rstrip("/")
    model = model or os.environ.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
    url = f"{base}/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {e.code}: {err_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e}") from e
    payload = json.loads(raw)
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"unexpected response shape: {raw[:500]}") from e
    return {
        "ok": True,
        "http_status": status,
        "model": model,
        "base_url": base,
        "content": content,
        "usage": payload.get("usage"),
        "raw_id": payload.get("id"),
    }


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fence if model ignored instructions
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            return {"commands": obj, "notes": ""}
    except json.JSONDecodeError:
        pass
    # brace scan
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        obj = json.loads(text[start : end + 1])
        if isinstance(obj, dict):
            return obj
    raise ValueError("model output is not a JSON object")


def normalize_plan(obj: dict[str, Any]) -> dict[str, Any]:
    cmds = obj.get("commands")
    if cmds is None and isinstance(obj.get("plan"), list):
        cmds = obj["plan"]
    if not isinstance(cmds, list):
        raise ValueError("plan missing commands list")
    out = []
    for i, c in enumerate(cmds):
        if isinstance(c, str):
            raise ValueError(f"command[{i}] must be object, got string")
        if not isinstance(c, dict):
            raise ValueError(f"command[{i}] invalid type")
        name = c.get("command") or c.get("cmd") or c.get("name")
        if not name or not isinstance(name, str):
            raise ValueError(f"command[{i}] missing command name")
        name = name.strip()
        if name not in ALLOWED_COMMANDS:
            raise ValueError(f"command[{i}] not allowed: {name}")
        args = c.get("args") or c.get("argv") or []
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError(f"command[{i}] args must be list[str]")
        label = c.get("label") or f"step_{i+1}_{name}"
        out.append({"label": str(label), "command": name, "args": list(args)})
    return {"commands": out, "notes": str(obj.get("notes") or "")}


def build_user_prompt(prompt_text: str, scene: str, fixture: str, extra: str = "") -> str:
    parts = [
        f"Scene path: {scene}",
        f"Fixture: {fixture}",
        f"User task:\n{prompt_text}",
    ]
    if extra:
        parts.append(f"Extra context:\n{extra}")
    parts.append("Return the JSON plan now.")
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="DeepSeek chat client for Prompt2Scene")
    ap.add_argument("--dotenv", default="", help="Optional .env path to load if key unset")
    ap.add_argument("--model", default="", help="Override DEEPSEEK_MODEL")
    ap.add_argument("--base-url", default="", help="Override DEEPSEEK_BASE_URL")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--system", default="", help="Override system prompt")
    ap.add_argument("--user", default="", help="User message (or use --prompt-file)")
    ap.add_argument("--prompt-file", default="", help="Read user message from file")
    ap.add_argument("--plan", action="store_true", help="Ask for Unity CLI JSON plan (uses default system)")
    ap.add_argument("--scene", default="", help="Scene path for --plan")
    ap.add_argument("--fixture", default="", help="Fixture id for --plan")
    ap.add_argument("--task", default="", help="Task text for --plan")
    ap.add_argument("--extra", default="", help="Extra context for --plan (e.g. check failures)")
    ap.add_argument("--out", default="", help="Write full result JSON to this path")
    args = ap.parse_args()

    if args.dotenv:
        load_dotenv(args.dotenv)

    if args.plan:
        task = args.task or args.user
        if not task and args.prompt_file:
            task = open(args.prompt_file, encoding="utf-8").read()
        if not task:
            print(json.dumps({"ok": False, "error": "--plan needs --task/--user/--prompt-file"}), file=sys.stderr)
            return 2
        system = args.system or SYSTEM_PROMPT
        user = build_user_prompt(task, args.scene or "(unspecified)", args.fixture or "(unspecified)", args.extra)
    else:
        system = args.system or "You are a helpful assistant."
        if args.prompt_file:
            user = open(args.prompt_file, encoding="utf-8").read()
        else:
            user = args.user
        if not user:
            print(json.dumps({"ok": False, "error": "need --user or --prompt-file"}), file=sys.stderr)
            return 2

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        result = chat(
            messages,
            model=args.model or None,
            base_url=args.base_url or None,
            temperature=args.temperature,
        )
    except Exception as e:
        err = {"ok": False, "error": str(e)}
        print(json.dumps(err, ensure_ascii=False))
        if args.out:
            open(args.out, "w", encoding="utf-8").write(json.dumps(err, indent=2, ensure_ascii=False) + "\n")
        return 1

    if args.plan:
        try:
            plan = normalize_plan(extract_json_object(result["content"]))
            result["plan"] = plan
            result["plan_ok"] = True
        except Exception as e:
            result["plan_ok"] = False
            result["plan_error"] = str(e)
            result["plan"] = {"commands": [], "notes": ""}

    text = json.dumps(result, ensure_ascii=False)
    print(text)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0 if result.get("ok") and (not args.plan or result.get("plan_ok")) else 1


if __name__ == "__main__":
    sys.exit(main())
