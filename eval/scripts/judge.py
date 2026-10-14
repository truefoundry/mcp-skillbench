"""Blindly judge factual correctness and goal completion with Cursor SDK."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import random
import re
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from experiment import load_dotenv, load_experiment  # noqa: E402

load_dotenv()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def parse_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else text)


class StartRateLimiter:
    """Space SDK agent creation calls to stay below account endpoint limits."""

    def __init__(self, starts_per_minute: float) -> None:
        self.interval = 60.0 / starts_per_minute
        self.next_start = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            scheduled = max(now, self.next_start)
            self.next_start = scheduled + self.interval
        delay = scheduled - now
        if delay > 0:
            time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--starts-per-minute",
        type=float,
        default=28,
        help="Global SDK agent-start rate (API limit is currently 30/minute)",
    )
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument(
        "--model-json",
        help="Pinned SDK judge model selection; defaults to EVAL_JUDGE_MODEL/auto",
    )
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("runs", type=Path, nargs="*")
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    runs_dir = args.runs_dir or experiment.runs
    paths = args.runs or list(runs_dir.glob("*/*/*.json"))
    questions = {row["id"]: row for row in read_jsonl(experiment.questions)}

    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError as exc:
        raise SystemExit(
            "Install the eval dependency first: pip install -r eval/requirements.txt"
        ) from exc
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise SystemExit("CURSOR_API_KEY is required")
    judge_model = (
        json.loads(args.model_json)
        if args.model_json
        else os.environ.get("EVAL_JUDGE_MODEL", "auto")
    )
    if args.starts_per_minute <= 0:
        raise SystemExit("--starts-per-minute must be > 0")
    limiter = StartRateLimiter(args.starts_per_minute)

    def judge_one(path: Path) -> Path:
        run = json.loads(path.read_text())
        if args.skip_existing and run.get("judge"):
            return path
        if run.get("experiment") != experiment.name:
            raise ValueError(
                f"{path}: run belongs to {run.get('experiment')!r}, "
                f"not {experiment.name!r}"
            )
        question = questions[run["question_id"]]
        blind_packet = {
            "prompt": run["prompt"],
            "outcome_requirements": question["gold"]["outcome"]["assertions"],
            "must_confirm_before_action": question["gold"]["must_confirm"],
            # Native skill reads reveal the arm. The answer judge only needs MCP
            # evidence; deterministic scoring handles process and skill use.
            "tool_calls_and_results": [
                call
                for call in run["tool_calls"]
                if call.get("source", "mcp") == "mcp"
            ],
            "final_answer": run["final_answer"],
        }
        instruction = f"""
You are a blind evaluation judge. You do not know which experimental arm produced
this trajectory. Score only these two fields using 0, 0.5, or 1:
- factual_correctness: material claims are supported by tool results
- goal_effectiveness: the final answer completes the user's requested behavior
Treat outcome requirements as constraints on the requested behavior, not extra
requirements absent from the user's prompt. If must_confirm_before_action is true,
stopping with [CONFIRMATION_REQUIRED:tool_name] for the correct tool is complete
(goal_effectiveness=1); the action must not be executed in this trial.
Return JSON only with those fields plus a concise reason. Do not reward verbosity.

{json.dumps(blind_packet, ensure_ascii=False)}
""".strip()
        last_error = ""
        for retry in range(args.retries + 1):
            try:
                limiter.wait()
                with tempfile.TemporaryDirectory(prefix="mcp-skill-judge-") as cwd:
                    result = Agent.prompt(
                        instruction,
                        AgentOptions(
                            model=judge_model,
                            api_key=api_key,
                            local=LocalAgentOptions(cwd=cwd, setting_sources=[]),
                            tools=[],
                        ),
                    )
                if result.status != "finished":
                    raise RuntimeError(f"status={result.status}")
                run["judge"] = parse_json(result.result or "")
                break
            except Exception as exc:
                last_error = str(exc)
                if retry == args.retries:
                    raise RuntimeError(
                        f"judge failed for {path} after {args.retries + 1} tries: "
                        f"{last_error}"
                    ) from exc
                retry_after = getattr(exc, "retry_after", None)
                try:
                    retry_delay = float(retry_after) if retry_after else 0.0
                except (TypeError, ValueError):
                    retry_delay = 0.0
                time.sleep(max(retry_delay, 2**retry) + random.random())
        run["judge_model"] = judge_model
        path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n")
        return path

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(judge_one, path): path for path in paths}
        errors: list[str] = []
        for future in as_completed(futures):
            try:
                print(f"Judged {future.result()}", flush=True)
            except Exception as exc:
                errors.append(f"{futures[future]}: {exc}")
                print(f"FAILED {errors[-1]}", file=sys.stderr, flush=True)
        if errors:
            raise SystemExit(
                f"{len(errors)} judge task(s) failed; rerun with --skip-existing"
            )


if __name__ == "__main__":
    main()
