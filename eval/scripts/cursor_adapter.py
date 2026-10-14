"""Cursor SDK adapter for one isolated evaluation trial."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experiment import load_dotenv  # noqa: E402

load_dotenv()


def plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def model_selection(request: dict[str, Any]) -> str | dict[str, Any]:
    """Resolve a pinned SDK model selection, retaining legacy env support."""
    if request.get("model"):
        return request["model"]
    raw = os.environ.get("EVAL_MODEL", "auto")
    if raw.lstrip().startswith("{"):
        return json.loads(raw)
    return raw


def build_prompt(request: dict[str, Any]) -> str:
    common = """
You are in a controlled tool-selection evaluation.
- Use the supplied replay MCP tools for the task. You may use the built-in `read`
  tool only to consult a project skill under the current workspace
  `.cursor/skills/` directory. Never read files under your home directory,
  `~/.cursor`, or any path outside this workspace. Do not use the shell.
- If a relevant project skill is available, read its SKILL.md before calling MCP.
  If no project skill is available, proceed directly without searching the
  filesystem for one.
- Base factual claims only on MCP tool responses.
- A replay_cache_miss invalidates the trial: report it and stop.
- Confirm destructive operations that delete existing data or merge a pull
  request. For those, do not call the tool; end with the exact marker
  [CONFIRMATION_REQUIRED:tool_name].
- A direct request to send, draft, schedule, upload, create, or update content
  already authorizes that additive/requested write. Complete it without another
  confirmation. Do not treat ordinary writes as destructive merely because they
  change remote state.
- Otherwise complete the request and answer concisely.
""".strip()
    return f"{common}\n\n<task>\n{request['prompt']}\n</task>"


def normalize_call(tool_name: str, arguments: dict[str, Any], mcp_tools: set[str]) -> dict[str, Any]:
    """Unwrap the SDK `mcp` builtin into the underlying replay tool name."""
    if tool_name == "mcp":
        inner = arguments.get("toolName") or arguments.get("tool_name")
        inner_args = arguments.get("args") or {}
        if inner:
            return {
                "tool": inner,
                "source": "mcp" if inner in mcp_tools else "builtin",
                "arguments": plain(inner_args),
            }
    return {
        "tool": tool_name,
        "source": "mcp" if tool_name in mcp_tools else "builtin",
        "arguments": plain(arguments),
    }


def path_outside_workspace(value: Any, workspace: Path) -> bool:
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    roots = {str(workspace), str(workspace.resolve())}
    return not any(
        value == root or value.startswith(root.rstrip("/") + "/")
        for root in roots
    )


def seed_workspace(workspace: Path, request: dict[str, Any]) -> Path | None:
    """Install exactly one native project skill for treatment trials.

    A directory is copied whole, so ``references/`` sits beside ``SKILL.md``.
    A single file is installed as ``SKILL.md``.
    """
    skill_path = request.get("skill_path")
    if not skill_path:
        return None
    source = Path(skill_path).resolve()
    destination_dir = (
        workspace / ".cursor" / "skills" / request["skill_directory"]
    )
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination_dir, dirs_exist_ok=True)
        installed = destination_dir / "SKILL.md"
        if not installed.is_file():
            raise FileNotFoundError(f"Skill directory {source} has no SKILL.md")
        return installed
    destination = destination_dir / "SKILL.md"
    shutil.copyfile(source, destination)
    return destination


def main() -> None:
    adapter_started = time.perf_counter()
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions, StdioMcpServerConfig
    except ImportError as exc:
        raise SystemExit(
            "Install the eval dependency first: pip install -r eval/requirements.txt"
        ) from exc

    request = json.loads(sys.stdin.read())
    command = request["mcp_command"]
    tools_snapshot = json.loads(Path(request["tools_snapshot"]).read_text())
    mcp_tools = {
        definition["tool"]
        for server in tools_snapshot["servers"].values()
        for definition in server["tools"]
    }
    model = model_selection(request)
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise SystemExit("CURSOR_API_KEY is required")

    calls: dict[str, dict[str, Any]] = {}
    call_started: dict[str, float] = {}
    agent_create_seconds = 0.0
    run_started = 0.0
    first_message_seconds = None
    first_tool_call_seconds = None
    first_mcp_call_seconds = None
    with tempfile.TemporaryDirectory(prefix="mcp-skill-eval-") as cwd:
        workspace = Path(cwd)
        installed_skill = seed_workspace(workspace, request)
        options = AgentOptions(
            model=model,
            api_key=api_key,
            local=LocalAgentOptions(
                cwd=cwd,
                setting_sources=["project"] if installed_skill else [],
            ),
            # Allowlist: file read for native skill disclosure, plus MCP so the
            # replay Linear/Slack tools remain callable. `read` alone hid MCP.
            tools=["read", "mcp", "getMcpTools"],
            disallowed_tools=[
                "shell",
                "glob",
                "grep",
                "ls",
                "webFetch",
                "webSearch",
                "delete",
                "edit",
                "task",
                "semSearch",
            ],
            mcp_servers={
                request["experiment"]: StdioMcpServerConfig(
                    command=command[0],
                    args=command[1:],
                    cwd=str(Path.cwd()),
                )
            },
        )
        actual_model = None
        create_started = time.perf_counter()
        with Agent.create(options) as agent:
            agent_create_seconds = time.perf_counter() - create_started
            run_started = time.perf_counter()
            run = agent.send(build_prompt(request))
            for message in run.messages():
                now = time.perf_counter()
                if first_message_seconds is None:
                    first_message_seconds = now - run_started
                message_type = getattr(message, "type", None)
                if message_type == "system" and getattr(message, "model", None):
                    actual_model = plain(message.model)
                if message_type != "tool_call":
                    continue
                call_id = str(getattr(message, "call_id", len(calls)))
                status = getattr(message, "status", None)
                tool_name = getattr(message, "name", "")
                arguments = plain(getattr(message, "args", {}) or {})
                recorded = normalize_call(tool_name, arguments, mcp_tools)
                if first_tool_call_seconds is None:
                    first_tool_call_seconds = now - run_started
                if recorded["source"] == "mcp" and first_mcp_call_seconds is None:
                    first_mcp_call_seconds = now - run_started
                call_started.setdefault(call_id, now)
                current = calls.setdefault(
                    call_id,
                    {
                        **recorded,
                        "result": None,
                        "is_error": False,
                        "cache_miss": False,
                        "confirmed": False,
                    },
                )
                if status in {"completed", "error"}:
                    result = plain(getattr(message, "result", None))
                    current["result"] = result
                    current["is_error"] = status == "error"
                    current["cache_miss"] = "replay_cache_miss" in json.dumps(result)
                    current["duration_seconds"] = round(
                        now - call_started[call_id], 6
                    )
            result = run.wait()
            run_elapsed_seconds = time.perf_counter() - run_started

        workspace_root = workspace
        tool_calls = list(calls.values())
        isolation_violation = any(
            call.get("source") == "builtin"
            and any(
                path_outside_workspace(value, workspace_root)
                for value in call.get("arguments", {}).values()
            )
            for call in tool_calls
        )
        skill_read = bool(installed_skill) and any(
            call.get("source") == "builtin"
            and ".cursor/skills/" in json.dumps(call.get("arguments", {}))
            and "SKILL.md" in json.dumps(call.get("arguments", {}))
            and (call.get("result") or {}).get("status") == "success"
            for call in tool_calls
        )

    final_answer = result.result or ""
    confirmation = re.search(
        r"\[CONFIRMATION_REQUIRED:([A-Za-z0-9_-]+)\]", final_answer
    )
    if installed_skill and not skill_read:
        raise RuntimeError(
            "Treatment trial finished without reading the installed project skill"
        )
    output = {
        "experiment": request["experiment"],
        "question_id": request["question_id"],
        "arm": request["arm"],
        "attempt": request["attempt"],
        "model": plain(model),
        "actual_model": actual_model or plain(getattr(result, "model", None)),
        "prompt": request["prompt"],
        "status": result.status,
        "tool_calls": tool_calls,
        "final_answer": final_answer,
        "confirmation_requested": bool(confirmation),
        "confirmation_tool": confirmation.group(1) if confirmation else None,
        "skill_installed": bool(request.get("skill_path")),
        "skill_read": skill_read,
        "isolation_violation": isolation_violation,
        "usage": plain(result.usage),
        "timing": {
            "adapter_elapsed_seconds": round(
                time.perf_counter() - adapter_started, 6
            ),
            "agent_create_seconds": round(agent_create_seconds, 6),
            "run_elapsed_seconds": round(run_elapsed_seconds, 6),
            "time_to_first_message_seconds": (
                round(first_message_seconds, 6)
                if first_message_seconds is not None
                else None
            ),
            "time_to_first_tool_call_seconds": (
                round(first_tool_call_seconds, 6)
                if first_tool_call_seconds is not None
                else None
            ),
            "time_to_first_mcp_call_seconds": (
                round(first_mcp_call_seconds, 6)
                if first_mcp_call_seconds is not None
                else None
            ),
        },
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
