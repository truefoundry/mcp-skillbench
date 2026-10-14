"""Build a leakage-safe packet for an external gold-labeling model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from experiment import load_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    output = args.output or experiment.directory / "labeling_packet.json"

    tools = json.loads(experiment.tools.read_text())
    prompts = []
    for line in experiment.questions.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            prompts.append(
                {
                    "id": row["id"],
                    "class": row["class"],
                    "servers": row["servers"],
                    "prompt": row["prompt"],
                }
            )

    packet = {
        "instruction": (
            "Label each prompt using only the frozen tool schemas and official "
            "documentation. Do not consult either treatment skill. Return primary "
            "tools, allowed resolution prefixes, acceptable sequences, forbidden "
            "lookalike tools, required arguments, and a one-sentence justification."
        ),
        "forbidden_inputs": [experiment.config["skill"]],
        "official_sources": experiment.config["official_sources"],
        "tools": tools,
        "prompts": prompts,
    }
    output.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote leakage-safe labeling packet to {output}")


if __name__ == "__main__":
    main()
