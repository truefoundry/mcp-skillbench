"""Render a readable human-review sheet from the JSONL bank."""

from __future__ import annotations

import json
import sys
import argparse
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_eval import render  # noqa: E402
from experiment import load_experiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    fixtures = json.loads(experiment.fixtures.read_text())
    groups: dict[str, list[dict]] = defaultdict(list)
    for line in experiment.questions.read_text().splitlines():
        if line.strip():
            item = json.loads(line)
            groups[item["class"]].append(item)

    lines = [
        "# Gold-label review sheet",
        "",
        "Review tool choices against `tools_list.json`, not the treatment skills.",
        "Approved labels must then be marked `approved` in `questions.jsonl`.",
        "",
    ]
    for class_name, items in groups.items():
        lines.extend([f"## {class_name}", ""])
        for item in items:
            gold = item["gold"]
            checkbox = "x" if item.get("review_status") == "approved" else " "
            sequences = [
                " → ".join(seq) if seq else "(no tool call expected)"
                for seq in gold["acceptable_sequences"]
            ]
            lines.extend(
                [
                    f"### [{checkbox}] {item['id']}",
                    "",
                    f"- Prompt: {render(item['prompt'], fixtures)}",
                    f"- Acceptable: {'; '.join(sequences)}",
                    f"- Forbidden first: {', '.join(gold['forbidden_first_tools'])}",
                ]
            )
            if gold.get("forbidden_tools"):
                lines.append(
                    f"- Forbidden anywhere: {', '.join(gold['forbidden_tools'])}"
                )
            if gold.get("required_arguments"):
                required = "; ".join(
                    f"{tool}({', '.join(f'{k}={v}' for k, v in expected.items())})"
                    for tool, expected in gold["required_arguments"].items()
                )
                lines.append(f"- Required arguments: {required}")
            if gold.get("resolution_prefix_allowed"):
                lines.append(
                    f"- Resolution calls allowed: {', '.join(gold['resolution_prefix_allowed'])}"
                )
            lines.extend(
                [
                    f"- Confirm first: {gold['must_confirm']}",
                    "- Expected answer: "
                    + " ".join(gold["outcome"]["assertions"]),
                    f"- Why: {item['justification']}",
                    "",
                ]
            )
    destination = experiment.directory / "REVIEW.md"
    destination.write_text("\n".join(lines))
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
