"""Check experiment freeze manifests against the files in this checkout."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ("linear", "slack")
MANIFESTS = ("FREEZE.json",)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_digest(cache: Path) -> tuple[str, int]:
    files = sorted(cache.rglob("*.json"))
    digest = hashlib.sha256(
        "".join(f"{path.relative_to(cache)}:{sha256(path)}\n" for path in files).encode()
    ).hexdigest()
    return digest, len(files)


def check(path: Path) -> None:
    payload = json.loads(path.read_text())
    for relative, expected in payload["files"].items():
        actual = sha256(PROJECT / relative)
        if actual != expected:
            raise SystemExit(f"{path}: {relative} hash changed")
    cache = PROJECT / "eval" / "experiments" / payload["experiment"] / "cache"
    digest, count = cache_digest(cache)
    if digest != payload["cache_sha256"] or count != payload["cache_files"]:
        raise SystemExit(f"{path}: replay cache digest changed")
    print(f"Verified {path.relative_to(PROJECT)}")


def main() -> None:
    for name in EXPERIMENTS:
        for manifest in MANIFESTS:
            check(PROJECT / "eval" / "experiments" / name / manifest)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as error:
        print(error, file=sys.stderr)
        raise
