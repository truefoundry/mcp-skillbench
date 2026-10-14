"""Render the pinned Claude model sweep as Markdown with full trial appendices."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import load_experiment  # noqa: E402
from results_md import (  # noqa: E402
    arm_totals,
    failure_reason,
    item_stats,
    table,
    write_trials,
)
from score import read_jsonl, score_item  # noqa: E402
from report import passes  # noqa: E402


def load_run_set(experiment_name: str, key: str) -> dict[str, Any]:
    experiment = load_experiment(experiment_name)
    questions_list = read_jsonl(experiment.questions)
    questions = {row["id"]: row for row in questions_list}
    root = experiment.directory / "model-runs" / key
    runs = {
        (run["arm"], run["question_id"], run["attempt"]): run
        for path in root.glob("*/*/*.json")
        for run in [json.loads(path.read_text())]
    }
    return {
        "experiment": experiment,
        "questions": questions,
        "order": [row["id"] for row in questions_list],
        "runs": runs,
        "report": json.loads((root / "report.json").read_text()),
        "root": root,
    }


def trial_rate(data: dict[str, Any], arm: str) -> tuple[int, int]:
    outcomes = [
        passes(score_item(data["questions"][run["question_id"]], run))
        for (run_arm, _, _), run in data["runs"].items()
        if run_arm == arm
    ]
    return sum(bool(outcome) for outcome in outcomes), len(outcomes)


def integrity(data: dict[str, Any]) -> tuple[int, int, int, int]:
    runs = list(data["runs"].values())
    return (
        len(runs),
        sum(
            bool(call.get("cache_miss"))
            for run in runs
            for call in run["tool_calls"]
        ),
        sum(bool(run.get("isolation_violation")) for run in runs),
        sum(
            run["arm"] == "treatment" and not run.get("skill_read")
            for run in runs
        ),
    )


def gold_mcp_calls(question: dict[str, Any]) -> int:
    gold = question["gold"]
    if gold["must_confirm"] or not gold["primary_tools"]:
        return 0
    return min(len(sequence) for sequence in gold["acceptable_sequences"])


def mean_mcp_calls(data: dict[str, Any], arm: str) -> float:
    runs = [run for run in data["runs"].values() if run["arm"] == arm]
    return sum(
        1
        for run in runs
        for call in run["tool_calls"]
        if call.get("source", "mcp") == "mcp"
    ) / len(runs)


def failing_rows(data: dict[str, Any]) -> list[list[str]]:
    rows = []
    for qid in data["order"]:
        base, total = item_stats(data, "baseline", qid)
        treatment, _ = item_stats(data, "treatment", qid)
        if base == total and treatment == total:
            continue
        diagnoses = []
        for arm in ("baseline", "treatment"):
            hits, _ = item_stats(data, arm, qid)
            if hits == total:
                continue
            failed = next(
                data["runs"][(arm, qid, attempt)]
                for attempt in (1, 2, 3)
                if not passes(
                    score_item(
                        data["questions"][qid],
                        data["runs"][(arm, qid, attempt)],
                    )
                )
            )
            diagnoses.append(
                f"{arm}: {failure_reason(data['questions'][qid], failed)[:180]}"
            )
        rows.append(
            [
                qid,
                data["questions"][qid]["class"],
                f"{base}/{total}",
                f"{treatment}/{total}",
                "<br>".join(diagnoses),
            ]
        )
    return rows


def main() -> None:
    config = json.loads((ROOT / "model_sweep.json").read_text())
    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    for model in config["models"]:
        key = model["key"]
        for experiment in ("linear", "slack"):
            data = load_run_set(experiment, key)
            loaded[(experiment, key)] = data
            write_trials(
                experiment,
                data,
                data["root"] / "TRIALS.md",
            )

    lines = [
        "# Claude model sweep: Linear and Slack MCP skills",
        "",
        "This is the corrected, pinned-model repeat of the isolated MCP-only versus",
        "MCP-plus-native-skill experiments. Each of six model configurations ran",
        "both arms three times on 19 Linear questions and 21 Slack questions:",
        "1,440 trajectories total. A single pinned Claude Opus 4.8-high judge scored",
        "factual correctness and goal effectiveness blind to arm identity.",
        "",
        "For the self-contained shareable analysis, including metric definitions,",
        "token/cost accounting, latency limitations, and every question, see",
        "[SKILL_EVAL_REPORT.md](SKILL_EVAL_REPORT.md). The pivotable workbook is",
        "[MODEL_SWEEP_RESULTS.xlsx](MODEL_SWEEP_RESULTS.xlsx).",
        "",
        "## Model matrix",
        "",
    ]
    model_rows = []
    for model in config["models"]:
        selection = model["selection"]
        params = ", ".join(
            f"{parameter['id']}={parameter['value']}"
            for parameter in selection["params"]
        )
        model_rows.append([model["key"], selection["id"], params])
    lines += table(["Run set", "Model ID", "Pinned parameters"], model_rows)
    judge = config["judge_model"]
    lines += [
        f"**Judge:** `{judge['id']}` with "
        + ", ".join(
            f"`{parameter['id']}={parameter['value']}`"
            for parameter in judge["params"]
        )
        + ".",
        "",
        "## Corrected harness",
        "",
        "This sweep deliberately supersedes the earlier `auto` run. It fixes four",
        "measurement defects before comparing models:",
        "",
        "1. Directly requested sends, drafts, schedules, uploads, creations, and",
        "   updates execute without a redundant confirmation stop; destructive",
        "   delete and merge operations still require confirmation.",
        "2. Allowed name/ID resolution calls no longer reduce execution efficiency.",
        "3. The Slack thread-draft question now supplies a message link and checks",
        "   the parent thread arguments.",
        "4. Missing replay profiles and observed off-gold read variants have stable,",
        "   sanitized recordings. Treatment trials are retried if they fail to read",
        "   the installed native skill.",
        "",
        "## Integrity",
        "",
    ]
    integrity_rows = []
    total_runs = total_misses = total_isolation = total_skips = 0
    for (experiment, key), data in loaded.items():
        runs, misses, isolation, skips = integrity(data)
        total_runs += runs
        total_misses += misses
        total_isolation += isolation
        total_skips += skips
        integrity_rows.append(
            [experiment.capitalize(), key, str(runs), str(misses), str(isolation), str(skips)]
        )
    lines += table(
        [
            "Server",
            "Run set",
            "Trials",
            "Cache misses",
            "Isolation violations",
            "Treatment skill skips",
        ],
        integrity_rows,
    )
    lines += [
        f"**Gate:** {total_runs} trials, {total_misses} cache misses, "
        f"{total_isolation} isolation violations, and {total_skips} treatment "
        "skill skips.",
        "",
        "## Headline results",
        "",
    ]
    headline = []
    for model in config["models"]:
        key = model["key"]
        for experiment in ("linear", "slack"):
            data = loaded[(experiment, key)]
            base_rate = trial_rate(data, "baseline")
            treatment_rate = trial_rate(data, "treatment")
            base = arm_totals(data, "baseline")
            treatment = arm_totals(data, "treatment")
            base_usage = data["report"]["usage"]["baseline"]
            treatment_usage = data["report"]["usage"]["treatment"]
            gold_calls = sum(
                gold_mcp_calls(data["questions"][qid]) for qid in data["order"]
            ) / len(data["order"])
            headline.append(
                [
                    experiment.capitalize(),
                    key,
                    f"{base_rate[0]}/{base_rate[1]} ({100 * base_rate[0] / base_rate[1]:.1f}%)",
                    f"{treatment_rate[0]}/{treatment_rate[1]} ({100 * treatment_rate[0] / treatment_rate[1]:.1f}%)",
                    f"{base['pass_at_3']}/{base['items']} → {treatment['pass_at_3']}/{treatment['items']}",
                    f"{base['strict']}/{base['items']} → {treatment['strict']}/{treatment['items']}",
                    f"{base_usage['input_tokens'] / base_usage['trials'] / 1000:.1f}k → "
                    f"{treatment_usage['input_tokens'] / treatment_usage['trials'] / 1000:.1f}k",
                    f"{base_usage['output_tokens'] / base_usage['trials'] / 1000:.2f}k → "
                    f"{treatment_usage['output_tokens'] / treatment_usage['trials'] / 1000:.2f}k",
                    f"${base_usage['mean_estimated_list_cost_usd']:.3f} → "
                    f"${treatment_usage['mean_estimated_list_cost_usd']:.3f}",
                    f"{base_usage['median_latency_seconds']:.1f}s → "
                    f"{treatment_usage['median_latency_seconds']:.1f}s",
                    f"{base_usage['p95_latency_seconds']:.1f}s → "
                    f"{treatment_usage['p95_latency_seconds']:.1f}s",
                    f"{gold_calls:.2f}; {mean_mcp_calls(data, 'baseline'):.2f} → "
                    f"{mean_mcp_calls(data, 'treatment'):.2f}",
                ]
            )
    lines += table(
        [
            "Server",
            "Model / effort",
            "Baseline trial pass",
            "Treatment trial pass",
            "Pass@3",
            "Strict reliability",
            "Mean input tokens",
            "Mean output tokens",
            "Estimated cost/trial",
            "Median latency",
            "p95 latency",
            "MCP calls (gold; no skill → skill)",
        ],
        headline,
    )
    lines += [
        "## Reading the result",
        "",
        "- Linear shows positive skill lift for all six model configurations. Fable",
        "  has the strongest absolute trial results; Sonnet gains from the skill but",
        "  remains less reliable than Opus and Fable.",
        "- Slack has positive trial-pass lift for both Sonnet and both Opus",
        "  configurations, is flat for Fable-medium, and is slightly negative for",
        "  Fable-high.",
        "- Output tokens decrease in every configuration. Treatment still has a",
        "  higher estimated list-price cost because reading the skill increases",
        "  input/cache usage in all 12 configurations.",
        "- Measured median latency improves in 10 of 12 configurations and p95",
        "  improves in 11 of 12. Both Linear Sonnet medians are slightly slower.",
        "- MCP calls move toward the shortest gold paths in most configurations;",
        "  skill-file reads are excluded because this metric counts MCP calls only.",
        "- Higher effort is not uniformly better. Compare the paired medium/high",
        "  rows per model and server rather than treating effort as a monotonic",
        "  quality control.",
        "",
        "## Per-configuration failures",
        "",
        "Counts are passing attempts out of three. Each diagnosis is from one",
        "representative failed attempt. Click the appendix link for every prompt,",
        "gold path, tool sequence, diagnosis, and final response from both arms.",
        "",
    ]
    for model in config["models"]:
        key = model["key"]
        for experiment in ("linear", "slack"):
            data = loaded[(experiment, key)]
            relative = (
                f"../../experiments/{experiment}/model-runs/{key}/TRIALS.md"
            )
            lines += [
                f"### {experiment.capitalize()} · {key}",
                "",
                f"[Full six-trial appendix]({relative})",
                "",
            ]
            rows = failing_rows(data)
            if rows:
                lines += table(
                    [
                        "Question",
                        "Class",
                        "Baseline",
                        "Treatment",
                        "Representative diagnosis",
                    ],
                    rows,
                )
            else:
                lines += ["All questions passed all three attempts in both arms.", ""]

    destination = ROOT / "results" / "sweep" / "MODEL_SWEEP_RESULTS.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
