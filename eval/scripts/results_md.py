"""Render the human-readable results report and per-trial appendices."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import load_experiment  # noqa: E402
from report import passes  # noqa: E402
from score import read_jsonl, score_item  # noqa: E402

EXPERIMENTS = ("linear", "slack")
def load(name: str) -> dict[str, Any]:
    experiment = load_experiment(name)
    questions = {row["id"]: row for row in read_jsonl(experiment.questions)}
    runs: dict[tuple[str, str, int], dict[str, Any]] = {}
    for path in experiment.runs.glob("*/*/*.json"):
        run = json.loads(path.read_text())
        runs[(run["arm"], run["question_id"], run["attempt"])] = run
    return {
        "experiment": experiment,
        "questions": questions,
        "order": [row["id"] for row in read_jsonl(experiment.questions)],
        "runs": runs,
        "report": json.loads((experiment.directory / "report.json").read_text()),
    }


def failure_reason(question: dict[str, Any], run: dict[str, Any]) -> str:
    scored = score_item(question, run)
    scores = scored["scores"]
    reasons = []
    if run.get("isolation_violation"):
        reasons.append("workspace isolation violated")
    if any(call.get("cache_miss") for call in run["tool_calls"]):
        reasons.append("replay cache miss")
    if scores["discoverability"] != 1:
        if scored["forbidden_tools_used"]:
            reasons.append(
                "used forbidden tool " + ", ".join(scored["forbidden_tools_used"])
            )
        elif question["gold"]["primary_tools"]:
            reasons.append(
                f"first substantive call was {scored['first_substantive_tool']}"
            )
        else:
            reasons.append("called a tool where the roster has no such capability")
    if scores["sequence_adherence"] != 1:
        reasons.append("gold sequence incomplete")
    if scores["argument_correctness"] != 1:
        reasons.append("required argument missing")
    if scores["security_policy"] != 1:
        reasons.append("security or confirmation rule broken")
    if scores["goal_effectiveness"] not in (1, 1.0):
        reasons.append(
            f"judge scored goal {scores['goal_effectiveness']}: "
            + (run.get("judge", {}).get("reason") or "").strip()
        )
    if (scores["factual_correctness"] or 0) < 0.5:
        reasons.append("judge scored factual correctness below 0.5")
    if scores["execution_efficiency"] < 0.7:
        reasons.append(
            f"efficiency {scores['execution_efficiency']} "
            f"({len([c for c in run['tool_calls'] if c.get('source', 'mcp') == 'mcp'])} MCP calls)"
        )
    return "; ".join(reasons) or "passed"


def mcp_sequence(run: dict[str, Any]) -> str:
    tools = [
        call["tool"]
        for call in run["tool_calls"]
        if call.get("source", "mcp") == "mcp"
    ]
    return " → ".join(tools) if tools else "(no MCP call)"


def trim(text: str) -> str:
    text = (text or "").strip()
    return text.replace("\n", "\n> ")


def item_stats(data: dict[str, Any], arm: str, qid: str) -> tuple[int, int]:
    outcomes = [
        passes(score_item(data["questions"][qid], data["runs"][(arm, qid, attempt)]))
        for attempt in (1, 2, 3)
    ]
    return sum(bool(outcome) for outcome in outcomes), len(outcomes)


def write_trials(
    name: str, data: dict[str, Any], destination: Path | None = None
) -> Path:
    lines = [
        f"# {name.capitalize()} trials: questions, gold, and both arms",
        "",
        "Every question in the frozen bank, its gold tool path, and all six judged",
        "trials (three baseline attempts without the skill, three treatment attempts",
        "with it). Final answers are reproduced verbatim.",
        "",
    ]
    for qid in data["order"]:
        question = data["questions"][qid]
        gold = question["gold"]
        sequences = " | ".join(
            " → ".join(sequence) if sequence else "(no substantive call)"
            for sequence in gold["acceptable_sequences"]
        )
        base_pass, base_total = item_stats(data, "baseline", qid)
        treat_pass, _ = item_stats(data, "treatment", qid)
        lines += [
            f"## {qid} · {question['class']}",
            "",
            f"**Prompt.** {data['runs'][('baseline', qid, 1)]['prompt']}",
            "",
            f"**Gold path.** {sequences}",
            "",
            f"**Gold outcome.** " + " ".join(gold["outcome"]["assertions"]),
            "",
            f"**Why this item exists.** {question['justification']}",
            "",
            f"**Result.** baseline {base_pass}/{base_total} attempts passed, "
            f"treatment {treat_pass}/{base_total}.",
            "",
        ]
        for arm, label in (("baseline", "Baseline (MCP only)"), ("treatment", "Treatment (MCP + skill)")):
            lines += [f"### {label}", ""]
            for attempt in (1, 2, 3):
                run = data["runs"][(arm, qid, attempt)]
                verdict = "PASS" if passes(score_item(question, run)) else "FAIL"
                lines += [
                    f"**Attempt {attempt} — {verdict}**",
                    "",
                    f"- Calls: {mcp_sequence(run)}",
                    f"- Diagnosis: {failure_reason(question, run)}",
                    "",
                    "> " + trim(run["final_answer"]),
                    "",
                ]
    destination = destination or data["experiment"].directory / "TRIALS.md"
    destination.write_text("\n".join(lines).rstrip() + "\n")
    return destination


def summary_rows(data: dict[str, Any]) -> list[list[str]]:
    rows = []
    for qid in data["order"]:
        base_pass, total = item_stats(data, "baseline", qid)
        treat_pass, _ = item_stats(data, "treatment", qid)
        rows.append(
            [
                qid,
                data["questions"][qid]["class"],
                f"{base_pass}/{total}",
                f"{treat_pass}/{total}",
            ]
        )
    return rows


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
        "",
    ]


def arm_totals(data: dict[str, Any], arm: str) -> dict[str, Any]:
    trials = [run for key, run in data["runs"].items() if key[0] == arm]
    outcomes = [
        passes(score_item(data["questions"][run["question_id"]], run))
        for run in trials
    ]
    items = data["report"]["items"]
    keys = [key for key in items if key.startswith(f"{arm}/")]
    return {
        "trials": len(trials),
        "trial_pass": sum(bool(outcome) for outcome in outcomes),
        "pass_at_3": sum(items[key]["pass_at_k"] for key in keys),
        "strict": sum(items[key]["strict_reliability"] for key in keys),
        "items": len(keys),
        "mean_tokens": data["report"]["usage"][arm]["mean_total_tokens"],
        "skill_read_rate": data["report"]["usage"][arm]["skill_read_rate"],
        "cache_misses": sum(
            1
            for run in trials
            for call in run["tool_calls"]
            if call.get("cache_miss")
        ),
        "isolation": sum(bool(run.get("isolation_violation")) for run in trials),
    }


def main() -> None:
    loaded = {name: load(name) for name in EXPERIMENTS}
    for name, data in loaded.items():
        print(f"Wrote {write_trials(name, data)}")

    lines = [
        "# MCP tool-selection skills: Linear and Slack results",
        "",
        "Two isolated experiments ask one question: does giving an agent a native",
        "project skill for an MCP server change which tools it picks, how reliably",
        "it finishes the task, and what it costs? Each experiment runs the same",
        "frozen question bank twice — once with the replay MCP server alone",
        "(*baseline*) and once with the identical server plus the skill",
        "(*treatment*) — three isolated attempts per question per arm.",
        "",
        "Per-question prompts, gold paths, and every trial answer are in",
        "[linear/TRIALS.md](../../experiments/linear/TRIALS.md) and",
        "[slack/TRIALS.md](../../experiments/slack/TRIALS.md).",
        "",
        "## Setup",
        "",
    ]
    lines += table(
        ["Setting", "Value"],
        [
            ["Agent runtime", "Cursor SDK local agent, one fresh subprocess per trial"],
            [
                "Agent model",
                "`auto` — `EVAL_MODEL` was never set, so every trial used the SDK's "
                "automatic model selection. The specific model is not pinned or "
                "recorded per trial.",
            ],
            [
                "Judge model",
                "`auto` as well (`EVAL_JUDGE_MODEL` unset), run blind on MCP "
                "evidence only",
            ],
            ["Tools allowed", "`read`, `mcp`, `getMcpTools`"],
            ["MCP", "record/replay proxy; writes are intercepted and never leave the proxy"],
            ["Skill delivery", "native project skill at `.cursor/skills/<name>/SKILL.md`"],
            ["Attempts", "3 per question per arm"],
        ],
    )
    lines += [
        "Because the model was `auto`, these numbers describe the skill's effect",
        "under Cursor's default model routing rather than a single pinned model.",
        "Pin `EVAL_MODEL` before using the numbers for a model-to-model comparison.",
        "",
        "## What each metric means",
        "",
        "Six rubric dimensions are scored per trial. Four are computed",
        "deterministically from the tool trajectory; two come from a blind judge",
        "that never sees the arm or the skill text.",
        "",
    ]
    lines += table(
        ["Metric", "Scored by", "Meaning", "Fails when"],
        [
            [
                "Discoverability",
                "trajectory",
                "Is the first substantive call the right tool? Channel/ID lookups "
                "listed as resolution prefixes don't count as substantive.",
                "The run opens with a forbidden or unrelated tool, uses any "
                "blacklisted tool anywhere, or calls a tool at all on a "
                "capability-gap item.",
            ],
            [
                "Sequence adherence",
                "trajectory",
                "Do the MCP calls contain a gold sequence in order? Extra reads in "
                "between are allowed.",
                "A required later step is missing or inverted — editing a canvas "
                "without reading it, scheduling without resolving the channel.",
            ],
            [
                "Execution efficiency",
                "trajectory",
                "Starts at 1.0; −0.15 per call beyond the shortest gold sequence, "
                "−0.25 per failed call.",
                "Below 0.7, i.e. roughly three or more redundant calls.",
            ],
            [
                "Security and policy",
                "trajectory",
                "Stays inside the requested search scope and confirms tools marked "
                "`must_confirm`.",
                "Crossing public/private boundaries, sending when asked to draft, "
                "or firing a destructive call without the confirmation marker.",
            ],
            [
                "Factual correctness",
                "blind judge",
                "Are the material claims supported by the replayed tool results? "
                "Scored 0, 0.5, or 1.",
                "Below 0.5 — contradicting, inventing, or ignoring recorded data.",
            ],
            [
                "Goal effectiveness",
                "blind judge",
                "Does the final answer complete the requested behavior? Reporting a "
                "real limitation counts as completion.",
                "Anything below 1 — wrong object, unsafe substitute, or a partial "
                "result.",
            ],
        ],
    )
    lines += [
        "**A trial passes** when discoverability, sequence adherence, security, and",
        "goal effectiveness all equal 1, factual correctness is at least 0.5, and",
        "efficiency is at least 0.7. From the three attempts per question:",
        "",
        "- **Trial pass rate** — passing trials out of all attempts; the raw rate.",
        "- **Pass@3** — the question counts if *any* of three attempts passed; this",
        "  is capability, \"can it do this at all\".",
        "- **Strict reliability** — the question counts only if *all three* passed;",
        "  this is consistency, and it is the number that matters for unattended",
        "  work.",
        "",
        "Two integrity counters accompany every run. **Replay cache misses** mean the",
        "agent asked for an argument combination that was never recorded, so that",
        "trial's result is an artifact of the harness rather than agent skill.",
        "**Isolation violations** mean a trial touched state outside its temporary",
        "workspace, which would contaminate the arm separation.",
        "",
        "## Headline results",
        "",
    ]
    rows = []
    for name, data in loaded.items():
        base = arm_totals(data, "baseline")
        treat = arm_totals(data, "treatment")
        rows.append(
            [
                name.capitalize(),
                f"{base['items']} questions · {base['trials'] + treat['trials']} trials",
                f"{base['trial_pass']}/{base['trials']} ({100 * base['trial_pass'] / base['trials']:.1f}%)",
                f"{treat['trial_pass']}/{treat['trials']} ({100 * treat['trial_pass'] / treat['trials']:.1f}%)",
                f"{base['pass_at_3']}/{base['items']} → {treat['pass_at_3']}/{treat['items']}",
                f"{base['strict']}/{base['items']} → {treat['strict']}/{treat['items']}",
                f"{base['mean_tokens'] / 1000:.1f}k → {treat['mean_tokens'] / 1000:.1f}k",
            ]
        )
    lines += table(
        [
            "Server",
            "Scale",
            "Baseline trial pass",
            "Treatment trial pass",
            "Pass@3",
            "Strict reliability",
            "Mean tokens/trial",
        ],
        rows,
    )
    integrity = []
    for name, data in loaded.items():
        base = arm_totals(data, "baseline")
        treat = arm_totals(data, "treatment")
        integrity.append(
            [
                name.capitalize(),
                str(base["cache_misses"] + treat["cache_misses"]),
                str(base["isolation"] + treat["isolation"]),
                f"{treat['skill_read_rate']:.0%} treatment / {base['skill_read_rate']:.0%} baseline",
            ]
        )
    lines += [
        "### Run integrity",
        "",
    ]
    lines += table(
        ["Server", "Replay cache misses", "Isolation violations", "Skill actually read"],
        integrity,
    )

    for name, data in loaded.items():
        lines += [
            f"## {name.capitalize()}: per-class trial pass rate",
            "",
        ]
        class_rows = []
        for class_name, entry in data["report"]["classes"].items():
            base = entry["baseline"]["trial_pass_rate"]
            treat = entry["treatment"]["trial_pass_rate"]
            class_rows.append(
                [
                    class_name,
                    str(entry["baseline"]["trials"]),
                    f"{100 * base:.0f}%",
                    f"{100 * treat:.0f}%",
                    f"{100 * (treat - base):+.0f} pp",
                ]
            )
        lines += table(
            ["Class", "Trials/arm", "Baseline", "Treatment", "Lift"], class_rows
        )
        lines += [
            f"### {name.capitalize()}: per-question attempts passed",
            "",
        ]
        lines += table(
            ["Question", "Class", "Baseline", "Treatment"], summary_rows(data)
        )

        failures = []
        for qid in data["order"]:
            for arm in ("baseline", "treatment"):
                hits, total = item_stats(data, arm, qid)
                if hits == total:
                    continue
                first_failing = next(
                    data["runs"][(arm, qid, attempt)]
                    for attempt in (1, 2, 3)
                    if not passes(
                        score_item(data["questions"][qid], data["runs"][(arm, qid, attempt)])
                    )
                )
                failures.append(
                    [
                        qid,
                        arm,
                        f"{total - hits}/{total}",
                        failure_reason(data["questions"][qid], first_failing)[:220],
                    ]
                )
        lines += [
            f"### {name.capitalize()}: what failed and why",
            "",
            "One representative failing attempt per question and arm.",
            "",
        ]
        lines += table(
            ["Question", "Arm", "Attempts failed", "Diagnosis"], failures
        )

        stops = {"baseline": 0, "treatment": 0}
        failing = {"baseline": 0, "treatment": 0}
        for (arm, qid, _attempt), run in data["runs"].items():
            if passes(score_item(data["questions"][qid], run)):
                continue
            failing[arm] += 1
            if run.get("confirmation_requested") and not data["questions"][qid]["gold"][
                "must_confirm"
            ]:
                stops[arm] += 1
        total_failing = failing["baseline"] + failing["treatment"]
        total_stops = stops["baseline"] + stops["treatment"]
        lines += [
            f"Of {total_failing} failing {name.capitalize()} trials, {total_stops} "
            f"({stops['baseline']} baseline, {stops['treatment']} treatment) failed "
            "for the same reason: the agent stopped and asked for confirmation on a "
            "write the prompt had already authorized. The rubric only treats a "
            "confirmation stop as complete for items marked `must_confirm`; "
            "everywhere else, halting before the write is an unfinished task.",
            "",
        ]

    destination = ROOT / "results" / "historical" / "RESULTS.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
