"""Report gold/trap tools that lack any recording or write-intercept rule."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))

from cache import ReplayCache  # noqa: E402
from experiment import load_experiment  # noqa: E402
from policy import is_write  # noqa: E402


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    questions = [
        json.loads(line)
        for line in experiment.questions.read_text().splitlines()
        if line.strip()
    ]
    snapshot = json.loads(experiment.tools.read_text())
    server_for = {
        tool["tool"]: server
        for server, data in snapshot["servers"].items()
        for tool in data["tools"]
    }
    recorded = {
        json.loads(path.read_text())["tool"]
        for path in experiment.cache.glob("*.json")
    }
    missing: dict[str, list[str]] = {}
    for item in questions:
        gold = item["gold"]
        needed = {
            *gold["primary_tools"],
            *gold["forbidden_first_tools"],
            *gold.get("forbidden_tools", []),
            *gold.get("resolution_prefix_allowed", []),
            *[tool for seq in gold["acceptable_sequences"] for tool in seq],
        }
        uncovered = sorted(
            tool
            for tool in needed
            if tool not in recorded and not is_write(server_for[tool], tool)
        )
        if uncovered:
            missing[item["id"]] = uncovered

    if missing:
        print("Cache coverage incomplete (tool-level preflight):")
        for item_id, tools in missing.items():
            print(f"- {item_id}: {', '.join(tools)}")
        raise SystemExit(1)
    defaults = ReplayCache(experiment.cache).tools_with_defaults()
    print("Every gold/trap tool has a recording or write intercept")
    print(f"{len(defaults)} tools have a default fallback for unrecorded arguments")


if __name__ == "__main__":
    main()
