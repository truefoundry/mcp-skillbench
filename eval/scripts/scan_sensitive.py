"""Fail if this checkout contains known private identifiers or secret material."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".venv", "__pycache__", "data"}
SKIP_FILES = {"scan_sensitive.py"}
PATTERNS = (
    re.compile(r"truefoundryworkspace"),
    re.compile(r"github\.com/truefoundry/(?:trueforge|helm-charts|servicefoundry-server)"),
    re.compile(r"linear\.app/truefoundry"),
    re.compile(r"Pfizer"),
    re.compile(r"Tanvi Mehta"),
    re.compile(r"C0AM68KU5GF"),
    re.compile(r"F0B5LF0UYTZ"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)


def scan(path: Path) -> list[str]:
    hits: list[str] = []
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return hits
    for pattern in PATTERNS:
        if pattern.search(text):
            hits.append(f"{path.relative_to(PROJECT)}: {pattern.pattern}")
    return hits


def main() -> None:
    hits: list[str] = []
    for path in PROJECT.rglob("*"):
        if (
            not path.is_file()
            or path.name in SKIP_FILES
            or any(part in SKIP_DIRS for part in path.parts)
        ):
            continue
        hits.extend(scan(path))
    if hits:
        print("\n".join(hits), file=sys.stderr)
        raise SystemExit(f"Found {len(hits)} prohibited pattern(s)")
    print("No prohibited identifiers or secret patterns")


if __name__ == "__main__":
    main()
