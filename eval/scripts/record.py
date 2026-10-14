"""Import captured MCP calls into the replay cache.

Input JSONL shape:
{"server":"linear","tool":"get_issue","arguments":{...},"response":{...}}

Add "default": true to also register the row as the tool's fallback response for
arguments that were never recorded (free-text search queries, mostly).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))

from cache import CacheEntry, ReplayCache  # noqa: E402
from experiment import load_experiment  # noqa: E402
from policy import is_write  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("capture", type=Path, nargs="?")
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    capture = args.capture or experiment.path("captures")

    cache = ReplayCache(experiment.cache)
    imported = 0
    defaults = 0
    for line_number, line in enumerate(capture.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        required = {"server", "tool", "arguments", "response"}
        missing = required - row.keys()
        if missing:
            raise ValueError(f"line {line_number}: missing {sorted(missing)}")
        if is_write(row["server"], row["tool"]):
            raise ValueError(
                f"line {line_number}: refusing to import live write {row['tool']}"
            )
        entry = CacheEntry(
            server=row["server"],
            tool=row["tool"],
            arguments=row["arguments"],
            response=row["response"],
            source=row.get("source", "live-recording"),
        )
        cache.put(entry)
        imported += 1
        if row.get("default"):
            cache.put_default(entry)
            defaults += 1
        if row.get("default_any"):
            cache.put_default(entry, ignore_selectors=True)
            defaults += 1
    print(
        f"Imported {imported} read-only recordings "
        f"({defaults} registered as tool defaults) into {experiment.cache}"
    )


if __name__ == "__main__":
    main()
