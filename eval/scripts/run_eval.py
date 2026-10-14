"""Run each question in a fresh external-agent subprocess.

The adapter command receives one JSON request on stdin and must return one JSON
trajectory on stdout. This keeps the eval independent of any single agent SDK.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import Experiment, load_dotenv, load_experiment  # noqa: E402

load_dotenv()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def render(template: str, fixtures: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in fixtures:
            raise KeyError(f"Missing fixture: {key}")
        return str(fixtures[key])

    return re.sub(r"\{\{([a-zA-Z0-9_]+)\}\}", replace, template)


def request_for(
    question: dict[str, Any],
    arm: str,
    attempt: int,
    fixtures: dict[str, Any],
    experiment: Experiment,
    model: dict[str, Any] | str,
) -> dict[str, Any]:
    return {
        "experiment": experiment.name,
        "question_id": question["id"],
        "prompt": render(question["prompt"], fixtures),
        "arm": arm,
        "attempt": attempt,
        "model": model,
        "skill_path": str(experiment.skill) if arm == "treatment" else None,
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
        "expected_output": {
            "question_id": question["id"],
            "arm": arm,
            "attempt": attempt,
            "tool_calls": [
                {
                    "tool": "string",
                    "arguments": {},
                    "result": {},
                    "is_error": False,
                    "cache_miss": False,
                    "confirmed": False,
                }
            ],
            "final_answer": "string",
            "confirmation_requested": False,
            "confirmation_tool": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument(
        "--command",
        default=f"{sys.executable} {ROOT / 'scripts' / 'cursor_adapter.py'}",
        help="Agent adapter command (defaults to the Cursor SDK adapter)",
    )
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=["baseline", "treatment"],
        default=["baseline", "treatment"],
    )
    parser.add_argument("--attempt-numbers", nargs="+", type=int)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--model-json",
        help='Pinned SDK model selection, e.g. {"id":"claude-opus-4-8","params":[...]}',
    )
    parser.add_argument(
        "--run-set",
        help="Store runs under model-runs/<run-set> instead of the legacy runs path",
    )
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    if args.jobs < 1 or args.retries < 0:
        raise SystemExit("--jobs must be >= 1 and --retries must be >= 0")
    experiment = load_experiment(args.experiment)
    model: dict[str, Any] | str = (
        json.loads(args.model_json)
        if args.model_json
        else os.environ.get("EVAL_MODEL", "auto")
    )
    if args.run_set and not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_set):
        raise SystemExit("--run-set may contain only letters, digits, dot, underscore, dash")
    runs_root = (
        experiment.directory / "model-runs" / args.run_set
        if args.run_set
        else experiment.runs
    )
    questions = read_jsonl(experiment.questions)
    selected = set(args.ids)
    if args.pilot:
        selected.update(experiment.config["pilot_ids"])
    if selected:
        unknown = selected - {item["id"] for item in questions}
        if unknown:
            raise SystemExit(f"Unknown question ids: {sorted(unknown)}")
        questions = [item for item in questions if item["id"] in selected]
    fixtures_path = args.fixtures or experiment.fixtures
    if fixtures_path.exists():
        fixtures = json.loads(fixtures_path.read_text())
    elif args.dry_run:
        fixtures = {
            key: f"<{key}>"
            for item in questions
            for key in re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", item["prompt"])
        }
    else:
        raise FileNotFoundError(
            f"{fixtures_path} is missing; copy fixtures.example.json and replace "
            "every value with a stable recording fixture"
        )

    attempts = args.attempt_numbers or list(range(1, args.attempts + 1))
    jobs: list[tuple[dict[str, Any], Path]] = []
    for question in questions:
        for arm in args.arms:
            for attempt in attempts:
                request = request_for(
                    question, arm, attempt, fixtures, experiment, model
                )
                output = runs_root / arm / question["id"] / f"{attempt}.json"
                if args.skip_existing and output.exists():
                    existing = json.loads(output.read_text())
                    # A resumed latency sweep must not mistake pre-instrumentation
                    # trajectories for completed work merely because the path exists.
                    if existing.get("timing", {}).get("run_elapsed_seconds") is not None:
                        continue
                if args.dry_run:
                    print(f"{output}: {request['prompt']}")
                    continue
                jobs.append((request, output))

    def run_one(item: tuple[dict[str, Any], Path]) -> tuple[Path, dict[str, Any]]:
        request, output = item
        last_error = ""
        for retry in range(args.retries + 1):
            completed = subprocess.run(
                shlex.split(args.command),
                input=json.dumps(request),
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode == 0:
                try:
                    trajectory = json.loads(completed.stdout)
                except json.JSONDecodeError as exc:
                    last_error = f"invalid adapter JSON: {exc}"
                else:
                    if trajectory.get("status") == "finished":
                        output.parent.mkdir(parents=True, exist_ok=True)
                        temporary = output.with_suffix(".json.tmp")
                        temporary.write_text(json.dumps(trajectory, indent=2) + "\n")
                        temporary.replace(output)
                        return output, trajectory
                    last_error = f"adapter status={trajectory.get('status')}"
            else:
                last_error = completed.stderr.strip() or f"exit {completed.returncode}"
            if retry < args.retries:
                time.sleep((2**retry) + random.random())
        raise RuntimeError(
            f"adapter failed for {request['question_id']}/{request['arm']}/"
            f"{request['attempt']} after {args.retries + 1} tries: {last_error}"
        )

    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_one, item): item for item in jobs}
        for future in as_completed(futures):
            request, _ = futures[future]
            try:
                output, trajectory = future.result()
            except Exception as exc:
                message = (
                    f"{request['question_id']}/{request['arm']}/"
                    f"{request['attempt']}: {exc}"
                )
                errors.append(message)
                print(f"FAILED {message}", file=sys.stderr, flush=True)
                continue
            print(
                f"wrote {output} status={trajectory.get('status')} "
                f"calls={len(trajectory.get('tool_calls', []))} "
                f"skill_read={trajectory.get('skill_read')}",
                flush=True,
            )
    if errors:
        raise SystemExit(f"{len(errors)} trial(s) failed; rerun with --skip-existing")


if __name__ == "__main__":
    main()
