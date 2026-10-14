"""Run, judge, and report the pinned-model Linear/Slack evaluation sweep."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def command(*parts: str) -> list[str]:
    return [sys.executable, *parts]


def run_checked(args: list[str]) -> None:
    print(f"+ {' '.join(args)}", flush=True)
    subprocess.run(args, cwd=PROJECT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=["trials", "judge", "report", "all"],
        default="all",
    )
    parser.add_argument("--jobs", type=int, default=12)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--experiments",
        nargs="+",
        choices=["linear", "slack"],
        default=["linear", "slack"],
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "model_sweep.json",
    )
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--run-set-suffix",
        default="",
        help="Store runs under model-runs/<model-key>-<suffix>",
    )
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=["baseline", "treatment"],
        default=["baseline", "treatment"],
    )
    args = parser.parse_args()
    if args.jobs < 1:
        raise SystemExit("--jobs must be >= 1")
    if args.run_set_suffix and not args.run_set_suffix.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("--run-set-suffix may contain only letters, digits, underscore, dash")

    config = json.loads(args.config.read_text())
    judge_model = json.dumps(config["judge_model"], separators=(",", ":"))
    phases = (
        ("trials", "judge", "report")
        if args.phase == "all"
        else (args.phase,)
    )

    for phase in phases:
        for model in config["models"]:
            key = model["key"]
            run_set = f"{key}-{args.run_set_suffix}" if args.run_set_suffix else key
            selection = json.dumps(model["selection"], separators=(",", ":"))
            for experiment in args.experiments:
                runs_dir = (
                    ROOT / "experiments" / experiment / "model-runs" / run_set
                )
                if phase == "trials":
                    cmd = command(
                        "eval/scripts/run_eval.py",
                        "--experiment",
                        experiment,
                        "--run-set",
                        run_set,
                        "--model-json",
                        selection,
                        "--attempts",
                        "3",
                        "--jobs",
                        str(args.jobs),
                        "--retries",
                        str(args.retries),
                        "--arms",
                        *args.arms,
                    )
                    if args.skip_existing:
                        cmd.append("--skip-existing")
                    run_checked(cmd)
                elif phase == "judge":
                    cmd = command(
                        "eval/scripts/judge.py",
                        "--experiment",
                        experiment,
                        "--runs-dir",
                        str(runs_dir),
                        "--model-json",
                        judge_model,
                        "--jobs",
                        str(args.jobs),
                        "--retries",
                        str(args.retries),
                    )
                    if args.skip_existing:
                        cmd.append("--skip-existing")
                    run_checked(cmd)
                else:
                    report = runs_dir / "report.json"
                    report.parent.mkdir(parents=True, exist_ok=True)
                    completed = subprocess.run(
                        command(
                            "eval/scripts/report.py",
                            "--experiment",
                            experiment,
                            "--runs-dir",
                            str(runs_dir),
                        ),
                        cwd=PROJECT,
                        check=True,
                        text=True,
                        capture_output=True,
                    )
                    report.write_text(completed.stdout)
                    print(f"Wrote {report}", flush=True)


if __name__ == "__main__":
    main()
