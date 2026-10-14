"""Validate question-bank structure, roster references, and class balance."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from experiment import load_experiment

ROOT = Path(__file__).resolve().parents[1]
# Only these items may declare an empty primary_tools list (correct answer is a
# stated limitation rather than a call).
NO_TOOL_CLASSES = {"capability_gap"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--require-reviewed", action="store_true")
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    bank = args.bank or experiment.questions
    tools = args.tools or experiment.tools

    snapshot = json.loads(tools.read_text())
    roster = {
        item["tool"]
        for server in snapshot["servers"].values()
        for item in server["tools"]
    }
    rows = read_jsonl(bank)
    errors: list[str] = []
    seen: set[str] = set()

    for row in rows:
        item_id = row.get("id", "<missing-id>")
        if item_id in seen:
            errors.append(f"{item_id}: duplicate id")
        seen.add(item_id)
        gold = row.get("gold", {})
        forbidden = gold.get("forbidden_first_tools", [])
        banned = gold.get("forbidden_tools", [])
        primary = gold.get("primary_tools", [])
        sequences = gold.get("acceptable_sequences", [])
        if not forbidden:
            errors.append(f"{item_id}: forbidden_first_tools must not be empty")
        tool_fields = [
            *gold.get("resolution_prefix_allowed", []),
            *primary,
            *forbidden,
            *banned,
            *[tool for seq in sequences for tool in seq],
            *gold.get("required_arguments", {}).keys(),
        ]
        unknown = sorted(set(tool_fields) - roster)
        if unknown:
            errors.append(f"{item_id}: unknown tools {unknown}")
        if not sequences:
            errors.append(f"{item_id}: no acceptable sequence")
        if set(primary) & (set(forbidden) | set(banned)):
            errors.append(f"{item_id}: tool is both primary and forbidden")
        if not primary and row.get("class") not in NO_TOOL_CLASSES:
            errors.append(f"{item_id}: empty primary_tools outside a capability-gap class")
        if primary and not any(set(seq) & set(primary) for seq in sequences):
            errors.append(f"{item_id}: no acceptable sequence contains a primary tool")
        for sequence in sequences:
            offending = sorted(set(sequence) & set(banned))
            if offending:
                errors.append(f"{item_id}: acceptable sequence uses banned tools {offending}")
        if not row.get("justification"):
            errors.append(f"{item_id}: missing justification")
        prompt = row.get("prompt", "")
        if any(tool in prompt for tool in roster):
            errors.append(f"{item_id}: prompt leaks a tool name")
        if args.require_reviewed and row.get("review_status") != "approved":
            errors.append(f"{item_id}: gold label is not user-approved")

    counts = Counter(row.get("class") for row in rows)
    expected_classes = experiment.config["expected_classes"]
    if counts != Counter(expected_classes):
        errors.append(
            f"class counts {dict(counts)} != expected {expected_classes}"
        )
    expected_total = sum(expected_classes.values())
    if len(rows) != expected_total:
        errors.append(f"expected {expected_total} questions, got {len(rows)}")

    if errors:
        raise SystemExit("Bank validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {len(rows)} questions against {len(roster)} live tools")
    print("Class counts:", dict(counts))


if __name__ == "__main__":
    main()
