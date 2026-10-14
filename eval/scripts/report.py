"""Aggregate run trajectories into per-class Pass@k and reliability lift."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score import read_jsonl, score_item  # noqa: E402
from experiment import load_experiment  # noqa: E402

MODEL_PRICING_PER_MILLION = {
    # Cursor's public list prices as of 2026-09-17. Cache-write prices use the
    # standard five-minute cache tier represented by the SDK usage fields.
    "claude-sonnet-4-6": {
        "input": 3.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
        "output": 15.0,
    },
    "claude-opus-4-8": {
        "input": 5.0,
        "cache_write": 6.25,
        "cache_read": 0.50,
        "output": 25.0,
    },
    "claude-fable-5": {
        "input": 10.0,
        "cache_write": 12.50,
        "cache_read": 1.0,
        "output": 50.0,
    },
}


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def passes(result: dict[str, Any]) -> bool | None:
    scores = result["scores"]
    if scores["factual_correctness"] is None or scores["goal_effectiveness"] is None:
        return None
    return (
        scores["discoverability"] == 1
        and scores["sequence_adherence"] == 1
        and scores["security_policy"] == 1
        and scores["goal_effectiveness"] == 1
        and scores["factual_correctness"] >= 0.5
        and scores["execution_efficiency"] >= 0.7
    )


def nested_number(value: dict[str, Any], *paths: tuple[str, ...]) -> float:
    for path in paths:
        current: Any = value
        for key in path:
            if not isinstance(current, dict):
                break
            current = current.get(key)
        else:
            if isinstance(current, (int, float)):
                return float(current)
    return 0.0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--runs-dir", type=Path)
    args = parser.parse_args()
    experiment = load_experiment(args.experiment)
    questions = {
        row["id"]: row for row in read_jsonl(experiment.questions)
    }
    runs_dir = args.runs_dir or experiment.runs
    run_paths = list(runs_dir.glob("*/*/*.json"))
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    unjudged = 0
    for path in run_paths:
        run = json.loads(path.read_text())
        if run.get("experiment") != experiment.name:
            raise ValueError(f"{path}: run belongs to another experiment")
        question = questions[run["question_id"]]
        outcome = passes(score_item(question, run))
        if outcome is None:
            unjudged += 1
            continue
        grouped[(run["arm"], question["class"])].append(outcome)

    models = {
        json.dumps(json.loads(path.read_text()).get("model"), sort_keys=True)
        for path in run_paths
    }
    judge_models = {
        json.dumps(json.loads(path.read_text()).get("judge_model"), sort_keys=True)
        for path in run_paths
    }
    summary: dict[str, Any] = {
        "unjudged_trials": unjudged,
        "models": [json.loads(model) for model in sorted(models)],
        "judge_models": [json.loads(model) for model in sorted(judge_models)],
        "classes": {},
    }
    classes = sorted({item["class"] for item in questions.values()})
    for class_name in classes:
        entry: dict[str, Any] = {}
        for arm in ("baseline", "treatment"):
            outcomes = grouped.get((arm, class_name), [])
            entry[arm] = {
                "trials": len(outcomes),
                "trial_pass_rate": (
                    sum(outcomes) / len(outcomes) if outcomes else None
                ),
            }
        baseline = entry["baseline"]["trial_pass_rate"]
        treatment = entry["treatment"]["trial_pass_rate"]
        entry["trial_pass_rate_lift"] = (
            treatment - baseline
            if baseline is not None and treatment is not None
            else None
        )
        summary["classes"][class_name] = entry

    # Per-question Pass@k and strict reliability.
    per_item: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for path in run_paths:
        run = json.loads(path.read_text())
        outcome = passes(score_item(questions[run["question_id"]], run))
        if outcome is not None:
            per_item[(run["arm"], run["question_id"])].append(outcome)
    summary["items"] = {
        f"{arm}/{item_id}": {
            "attempts": len(outcomes),
            "pass_at_k": any(outcomes),
            "strict_reliability": all(outcomes),
        }
        for (arm, item_id), outcomes in sorted(per_item.items())
    }
    usage: dict[str, dict[str, float]] = {}
    for arm in ("baseline", "treatment"):
        arm_runs = [
            json.loads(path.read_text())
            for path in run_paths
            if path.parts[-3] == arm
        ]
        totals = {
            "input_tokens": 0.0,
            "output_tokens": 0.0,
            "cache_read_tokens": 0.0,
            "cache_write_tokens": 0.0,
            "raw_cost_cents": 0.0,
            "charged_cents": 0.0,
        }
        for run in arm_runs:
            data = run.get("usage") or {}
            totals["input_tokens"] += nested_number(
                data, ("input_tokens",), ("usage", "input_tokens")
            )
            totals["output_tokens"] += nested_number(
                data, ("output_tokens",), ("usage", "output_tokens")
            )
            totals["cache_read_tokens"] += nested_number(
                data, ("cache_read_tokens",), ("usage", "cache_read_tokens")
            )
            totals["cache_write_tokens"] += nested_number(
                data, ("cache_write_tokens",), ("usage", "cache_write_tokens")
            )
            totals["raw_cost_cents"] += nested_number(
                data, ("cost", "raw_cost_cents")
            )
            totals["charged_cents"] += nested_number(
                data, ("cost", "charged_cents")
            )
        count = len(arm_runs)
        model_id = (
            (arm_runs[0].get("actual_model") or arm_runs[0].get("model") or {}).get("id")
            if arm_runs
            else None
        )
        pricing = MODEL_PRICING_PER_MILLION.get(model_id or "")
        # Cursor SDK input_tokens is the complete prompt-token count; cache read
        # and write are subsets used for pricing, not additional tokens.
        uncached_input_tokens = max(
            0.0,
            totals["input_tokens"]
            - totals["cache_read_tokens"]
            - totals["cache_write_tokens"],
        )
        estimated_list_cost = (
            (
                uncached_input_tokens * pricing["input"]
                + totals["cache_write_tokens"] * pricing["cache_write"]
                + totals["cache_read_tokens"] * pricing["cache_read"]
                + totals["output_tokens"] * pricing["output"]
            )
            / 1_000_000
            if pricing
            else None
        )
        elapsed = [
            float(run["timing"]["adapter_elapsed_seconds"])
            for run in arm_runs
            if (run.get("timing") or {}).get("adapter_elapsed_seconds") is not None
        ]
        first_mcp = [
            float(run["timing"]["time_to_first_mcp_call_seconds"])
            for run in arm_runs
            if (run.get("timing") or {}).get("time_to_first_mcp_call_seconds")
            is not None
        ]
        usage[arm] = {
            "trials": float(count),
            **totals,
            "uncached_input_tokens": uncached_input_tokens,
            "mean_total_tokens": (
                (
                    totals["input_tokens"]
                    + totals["output_tokens"]
                )
                / count
                if count
                else 0.0
            ),
            "estimated_list_cost_usd": estimated_list_cost,
            "mean_estimated_list_cost_usd": (
                estimated_list_cost / count
                if estimated_list_cost is not None and count
                else None
            ),
            "timed_trials": len(elapsed),
            "mean_latency_seconds": (
                sum(elapsed) / len(elapsed) if elapsed else None
            ),
            "median_latency_seconds": percentile(elapsed, 0.5),
            "p95_latency_seconds": percentile(elapsed, 0.95),
            "median_time_to_first_mcp_seconds": percentile(first_mcp, 0.5),
            "p95_time_to_first_mcp_seconds": percentile(first_mcp, 0.95),
            "skill_read_rate": (
                sum(bool(run.get("skill_read")) for run in arm_runs) / count
                if count
                else 0.0
            ),
        }
    summary["usage"] = usage
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
