"""Minimal stdio MCP replay server for the Linear + Slack evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cache import ReplayCache
from policy import is_write, synthetic_success


def load_tools(path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    snapshot = json.loads(path.read_text())
    tools: list[dict[str, Any]] = []
    routes: dict[str, str] = {}
    for server, data in snapshot["servers"].items():
        for definition in data["tools"]:
            name = definition["tool"]
            routes[name] = server
            tools.append(
                {
                    "name": name,
                    "description": definition["description"],
                    "inputSchema": definition.get("inputSchema", {"type": "object"}),
                }
            )
    return tools, routes


class ReplayServer:
    def __init__(self, tools_path: Path, cache_path: Path):
        self.tools, self.routes = load_tools(tools_path)
        self.cache = ReplayCache(cache_path)

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            return None

        if method == "initialize":
            result = {
                "protocolVersion": request.get("params", {}).get(
                    "protocolVersion", "2025-06-18"
                ),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "mcp-skills-replay", "version": "0.1.0"},
            }
            return self._result(request_id, result)

        if method == "ping":
            return self._result(request_id, {})

        if method == "tools/list":
            return self._result(request_id, {"tools": self.tools})

        if method == "tools/call":
            return self._call_tool(request_id, request.get("params", {}))

        return self._error(request_id, -32601, f"Method not found: {method}")

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        tool = params.get("name")
        arguments = params.get("arguments") or {}
        server = self.routes.get(tool)
        if server is None:
            return self._error(request_id, -32602, f"Unknown tool: {tool}")

        if is_write(server, tool):
            value = synthetic_success(server, tool, arguments)
            return self._tool_result(request_id, value)

        value = self.cache.get(server, tool, arguments)
        if value is None:
            # Both arms hit the same fallback, so phrasing differences in free-text
            # queries cannot bias the comparison.
            value = self.cache.get_default(server, tool, arguments)
        if value is None:
            miss = {
                "error": "replay_cache_miss",
                "server": server,
                "tool": tool,
                "arguments": arguments,
                "retryable": False,
            }
            return self._tool_result(request_id, miss, is_error=True)
        return self._tool_result(request_id, value)

    @staticmethod
    def _result(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    @staticmethod
    def _tool_result(
        request_id: Any, value: Any, *, is_error: bool = False
    ) -> dict[str, Any]:
        result = {
            "content": [
                {"type": "text", "text": json.dumps(value, ensure_ascii=False)}
            ],
            "isError": is_error,
        }
        return ReplayServer._result(request_id, result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tools", type=Path, default=Path("eval/tools_list.json"))
    parser.add_argument("--cache", type=Path, default=Path("eval/cache"))
    args = parser.parse_args()
    server = ReplayServer(args.tools, args.cache)

    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle(request)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:  # keep protocol errors machine-readable
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32603, "message": str(exc)},
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
