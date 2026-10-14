"""Unscored probes for native project-skill discovery and Read availability."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from experiment import load_dotenv, load_experiment  # noqa: E402

load_dotenv()


def request(experiment_name: str, treatment: bool) -> dict:
    experiment = load_experiment(experiment_name)
    return {
        "experiment": experiment.name,
        "question_id": "probe-native-skill" if treatment else "probe-read-tool",
        "prompt": (
            "Before using any MCP tool, identify and read the available project "
            f"skill relevant to {experiment.name}. Reply with its exact skill name."
            if treatment
            else "Reply exactly READY. Do not call an MCP tool or read a file."
        ),
        "arm": "treatment" if treatment else "baseline",
        "attempt": 0,
        "skill_path": str(experiment.skill) if treatment else None,
        "skill_directory": experiment.config["skill_directory"],
        "tools_snapshot": str(experiment.tools),
        "mcp_command": [
            "python3",
            str(ROOT / "proxy" / "server.py"),
            "--tools",
            str(experiment.tools),
            "--cache",
            str(experiment.cache),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    adapter = ROOT / "scripts" / "cursor_adapter.py"
    experiment.path("probes").mkdir(parents=True, exist_ok=True)

    for treatment in (False, True):
        payload = request(args.experiment, treatment)
        completed = subprocess.run(
            [sys.executable, str(adapter)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip())
        result = json.loads(completed.stdout)
        destination = experiment.path("probes") / f"{payload['question_id']}.json"
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {destination}")

    treatment_result = json.loads(
        (experiment.path("probes") / "probe-native-skill.json").read_text()
    )
    if not treatment_result.get("skill_read"):
        raise SystemExit(
            "Native skill was not read; do not run scored trials. "
            "Investigate discovery or explicitly choose inline fallback."
        )


if __name__ == "__main__":
    main()
