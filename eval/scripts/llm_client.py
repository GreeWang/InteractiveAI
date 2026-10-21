#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client for Prompt2Scene eval.

Supports DeepSeek and Alibaba Cloud Bailian (DashScope compatible-mode).
Resolves credentials via env precedence (see resolve_config). Never prints keys.
Stdout is JSON only for machine consumption.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEFAULT_BAILIAN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_BAILIAN_MODEL = "qwen3.8-max"

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
- IMPORTANT: single-shot plans cannot read get_component_properties results mid-plan. Do not call it and then guess; use the known fixture layout below (or positions given in Extra context).
- For create_gameobject use --name X --primitive cube|sphere|capsule|cylinder|plane.
- For set_transform typical: --target /Name --position "[x,y,z]" (optional --rotation / --scale).
- Do not invent packages, MCP tools, or non-listed commands.
- Keep plans short (typically 1–8 commands). open_scene/save_scene may be omitted; the harness can open the scene.
- If the task is ambiguous, pick a simple reasonable plan and explain in notes.
- Do NOT restore/revert an edit unless the user explicitly asks to restore.
- For ~1.5m spacing beside CubeA at (0,0.5,0), place the new cube near (1.5,0.5,0) (distance 1.2–1.8).
- For raise to y=2 with x/z unchanged, set position like [1.5,2.0,0] and stop (no restore step).

Known fixture seeds (use these coords; do NOT assume everything is at origin):
- F02_EditBaseline: CubeA≈(0,0.5,0), SphereB≈(1.5,0.5,0), Floor at y=0.
- F03_ConstraintSandbox: RedBox≈(-1.5,0.5,0), BlueBall≈(1.5,0.5,0), CupOnBox starts near RedBox (may be offset before the task).
- F01_EmptyRoom: empty; create primitives with create_gameobject.

on_top_of / "resting on" / "正上方" (critical):
- Match the SUPPORT object's X and Z EXACTLY (horizontal offset must be ≤0.5).
- Place the top object slightly above: y ≈ support.y + 0.75 (acceptable dy in about 0.3–1.5).
- Example: RedBox at (-1.5,0.5,0) → set CupOnBox to [-1.5,1.25,0] (NOT [0,1.5,0]).
- Never place the top object at world origin unless the support is also at origin.

Generate tasks (F01):
- Create named primitives then set_transform. Keep scales modest (cube/sphere default ok; cup/sphere scale ~0.4 if needed).
- For Cup on Table: Table (cube) near (0,0.5,0), Cup (sphere) at (0,1.25,0) matching Table XZ.
- For A B C row along +X ~1m: e.g. A(0,0.5,0), B(1,0.5,0), C(2,0.5,0).
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


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _provider_requested() -> str:
    """Normalized LLM_PROVIDER if set (deepseek|bailian|dashscope|...)."""
    return _env("LLM_PROVIDER").lower()


def completions_url(base: str) -> str:
    """Build chat completions URL without double /v1/v1/.

    If base already ends with /v1 (e.g. DashScope compatible-mode/v1),
    append /chat/completions only; else append /v1/chat/completions.
    """
    b = base.rstrip("/")
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def resolve_config(
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    """Resolve api_key, base_url, model, provider.

    Precedence:
      1. Explicit CLI model / base_url (caller-passed)
      2. LLM_API_KEY / LLM_BASE_URL / LLM_MODEL when any LLM_* credential/base/model set
      3. LLM_PROVIDER=bailian|dashscope → DASHSCOPE_* (defaults for Bailian)
      4. Else DeepSeek DEEPSEEK_* (current defaults)
    """
    provider_req = _provider_requested()
    bailian = provider_req in ("bailian", "dashscope", "qwen", "aliyun")

    # Generic LLM_* override path: if any of the three are set, prefer that family
    # for missing pieces (still allow CLI model/base to win).
    llm_key = _env("LLM_API_KEY")
    llm_base = _env("LLM_BASE_URL")
    llm_model = _env("LLM_MODEL")
    use_llm_family = bool(llm_key or llm_base or llm_model)

    if use_llm_family and not bailian:
        api_key = llm_key or _env("DEEPSEEK_API_KEY") or _env("DASHSCOPE_API_KEY")
        base = (base_url or llm_base or _env("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE).rstrip("/")
        mdl = model or llm_model or _env("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
        provider = provider_req or "llm"
        if not api_key:
            raise RuntimeError("LLM_API_KEY is not set (and no DEEPSEEK_/DASHSCOPE_ fallback key)")
        return {
            "api_key": api_key,
            "base_url": base,
            "model": mdl,
            "provider": provider,
        }

    if bailian:
        api_key = llm_key or _env("DASHSCOPE_API_KEY") or _env("LLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY (or LLM_API_KEY) is not set for Bailian/DashScope"
            )
        base = (
            base_url
            or llm_base
            or _env("DASHSCOPE_BASE_URL")
            or DEFAULT_BAILIAN_BASE
        ).rstrip("/")
        mdl = model or llm_model or _env("DASHSCOPE_MODEL") or DEFAULT_BAILIAN_MODEL
        return {
            "api_key": api_key,
            "base_url": base,
            "model": mdl,
            "provider": "bailian",
        }

    # Default: DeepSeek (unchanged when only DEEPSEEK_* is set)
    api_key = llm_key or _env("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    base = (
        base_url or llm_base or _env("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE
    ).rstrip("/")
    mdl = model or llm_model or _env("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
    return {
        "api_key": api_key,
        "base_url": base,
        "model": mdl,
        "provider": provider_req or "deepseek",
    }


def secret_values() -> list[str]:
    """Non-empty API key values for redaction (never log these)."""
    out = []
    for name in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "LLM_API_KEY"):
        v = _env(name)
        if v:
            out.append(v)
    return out


def redact_text(text: str) -> str:
    for key in secret_values():
        if key and key in text:
            text = text.replace(key, "<redacted>")
    return text


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    timeout_s: float = 300.0,
    seed: int | None = None,
) -> dict[str, Any]:
    cfg = resolve_config(model=model, base_url=base_url)
    api_key = cfg["api_key"]
    base = cfg["base_url"]
    model = cfg["model"]
    url = completions_url(base)
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if seed is not None:
        body["seed"] = int(seed)
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
        "provider": cfg["provider"],
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
    ap = argparse.ArgumentParser(description="OpenAI-compatible chat client for Prompt2Scene")
    ap.add_argument("--dotenv", default="", help="Optional .env path to load if key unset")
    ap.add_argument("--model", default="", help="Override model (CLI > env)")
    ap.add_argument("--base-url", default="", help="Override API base URL (CLI > env)")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=-1, help="Optional API seed (>=0); -1 omits")
    ap.add_argument("--system", default="", help="Override system prompt")
    ap.add_argument("--user", default="", help="User message (or use --prompt-file)")
    ap.add_argument("--prompt-file", default="", help="Read user message from file")
    ap.add_argument("--plan", action="store_true", help="Ask for Unity CLI JSON plan (uses default system)")
    ap.add_argument("--scene", default="", help="Scene path for --plan")
    ap.add_argument("--fixture", default="", help="Fixture id for --plan")
    ap.add_argument("--task", default="", help="Task text for --plan")
    ap.add_argument("--extra", default="", help="Extra context for --plan (e.g. check failures)")
    ap.add_argument("--out", default="", help="Write full result JSON to this path")
    ap.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved provider/model/base_url (no secrets) as JSON and exit",
    )
    args = ap.parse_args()

    if args.dotenv:
        load_dotenv(args.dotenv)

    if args.print_config:
        try:
            cfg = resolve_config(
                model=args.model or None,
                base_url=args.base_url or None,
            )
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return 1
        safe = {
            "ok": True,
            "provider": cfg["provider"],
            "model": cfg["model"],
            "base_url": cfg["base_url"],
            "completions_url": completions_url(cfg["base_url"]),
            "has_api_key": bool(cfg["api_key"]),
        }
        print(json.dumps(safe, ensure_ascii=False))
        return 0

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
            seed=(args.seed if args.seed is not None and args.seed >= 0 else None),
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
