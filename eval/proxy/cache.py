"""Canonical cache keys and JSONL-backed replay storage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# These change response verbosity or pagination, not the requested object/operation.
IGNORED_ARGUMENTS = {
    "cursor",
    "limit",
    "response_format",
    "format",
    "include_context",
    "max_context_length",
}

# Free-text search arguments cannot be matched byte-for-byte across trials, so each
# tool may also register one default response used when the exact key is absent.
DEFAULTS_DIRNAME = "defaults"

# Arguments that select between materially different result shapes, so they get their
# own default instead of sharing the tool's.
DEFAULT_SELECTORS: dict[str, tuple[str, ...]] = {
    "slack_search_public": ("content_types",),
    "slack_search_public_and_private": ("content_types",),
}


def _selector_suffix(tool: str, arguments: dict[str, Any] | None) -> str:
    if not arguments:
        return ""
    for key in DEFAULT_SELECTORS.get(tool, ()):
        value = arguments.get(key)
        if value is not None:
            slug = "".join(
                char if char.isalnum() else "-" for char in str(value)
            )
            return f".{key}-{slug}"
    return ""


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize(item)
            for key, item in sorted(value.items())
            if key not in IGNORED_ARGUMENTS and item is not None
        }
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def cache_key(server: str, tool: str, arguments: dict[str, Any]) -> str:
    semantic = {"server": server, "tool": tool, "arguments": normalize(arguments)}
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:20]


@dataclass(frozen=True)
class CacheEntry:
    server: str
    tool: str
    arguments: dict[str, Any]
    response: Any
    source: str = "recorded"

    @property
    def key(self) -> str:
        return cache_key(self.server, self.tool, self.arguments)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "server": self.server,
            "tool": self.tool,
            "arguments": normalize(self.arguments),
            "response": self.response,
            "source": self.source,
        }


class ReplayCache:
    def __init__(self, directory: Path):
        self.directory = directory
        self.defaults = directory / DEFAULTS_DIRNAME
        self.directory.mkdir(parents=True, exist_ok=True)
        self.defaults.mkdir(parents=True, exist_ok=True)

    def path_for(self, server: str, tool: str, arguments: dict[str, Any]) -> Path:
        return self.directory / f"{cache_key(server, tool, arguments)}.json"

    def default_path_for(
        self, server: str, tool: str, arguments: dict[str, Any] | None = None
    ) -> Path:
        return self.defaults / f"{server}.{tool}{_selector_suffix(tool, arguments)}.json"

    def get(self, server: str, tool: str, arguments: dict[str, Any]) -> Any | None:
        path = self.path_for(server, tool, arguments)
        if not path.exists():
            return None
        return json.loads(path.read_text())["response"]

    def get_default(
        self, server: str, tool: str, arguments: dict[str, Any] | None = None
    ) -> Any | None:
        for path in (
            self.default_path_for(server, tool, arguments),
            self.default_path_for(server, tool),
        ):
            if path.exists():
                return json.loads(path.read_text())["response"]
        return None

    def tools_with_defaults(self) -> set[str]:
        return {json.loads(path.read_text())["tool"] for path in self.defaults.glob("*.json")}

    def put(self, entry: CacheEntry) -> Path:
        path = self.directory / f"{entry.key}.json"
        path.write_text(json.dumps(entry.as_dict(), indent=2, ensure_ascii=False) + "\n")
        return path

    def put_default(self, entry: CacheEntry, *, ignore_selectors: bool = False) -> Path:
        path = self.default_path_for(
            entry.server, entry.tool, None if ignore_selectors else entry.arguments
        )
        path.write_text(json.dumps(entry.as_dict(), indent=2, ensure_ascii=False) + "\n")
        return path
