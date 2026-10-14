"""Hash experiment inputs after human label review."""

from __future__ import annotations

import hashlib
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
from experiment import load_experiment


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skill_files(skill: Path) -> list[Path]:
    if skill.is_dir():
        return sorted(path for path in skill.rglob("*") if path.is_file())
    return [skill]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    questions = [
        json.loads(line)
        for line in experiment.questions.read_text().splitlines()
        if line.strip()
    ]
    files = [
        experiment.directory / "config.json",
        experiment.tools,
        experiment.questions,
        experiment.fixtures,
        ROOT / "RUBRIC.md",
        *skill_files(experiment.skill),
    ]
    parity = experiment.directory / "PARITY.md"
    if parity.exists():
        files.append(parity)
    cache_files = sorted(experiment.cache.rglob("*.json"))
    cache_digest = hashlib.sha256(
        "".join(f"{path.relative_to(experiment.cache)}:{sha256(path)}\n" for path in cache_files).encode()
    ).hexdigest()
    payload = {
        "experiment": experiment.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label_review_complete": all(
            item.get("review_status") == "approved" for item in questions
        ),
        "files": {
            str(path.relative_to(PROJECT)): sha256(path)
            for path in files
        },
        "cache_sha256": cache_digest,
        "cache_files": len(cache_files),
    }
    destination = experiment.directory / "FREEZE.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
