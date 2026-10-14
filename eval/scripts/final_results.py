"""Write FINAL_RESULTS.md and its SVG figures.

Reporting only. No model is called. No-skill runs supply the baseline.
Progressive-skill runs supply the with-skill arm.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import load_experiment  # noqa: E402
from model_sweep_results import gold_mcp_calls  # noqa: E402
from model_sweep_xlsx import estimated_cost, mcp_call_count  # noqa: E402
from report import passes, percentile  # noqa: E402
from results_md import table  # noqa: E402
from score import read_jsonl, score_item  # noqa: E402
from skill_comparison import ARMS, EXPERIMENTS, V2_SUFFIX, load_runs  # noqa: E402

FIGURES = ROOT / "results" / "figures"
DESTINATION = PROJECT / "FINAL_RESULTS.md"
COLORS = {"no skill": "#9CA3AF", "with skill": "#10B981"}
SERVER_LABEL = {"linear": "Linear", "slack": "Slack"}


def arm_runs(
    v1: dict[tuple[str, str, int], dict[str, Any]],
    v2: dict[tuple[str, str, int], dict[str, Any]],
    version: str,
    arm: str,
) -> list[dict[str, Any]]:
    source = v1 if version == "baseline" else v2
    return [run for (run_arm, _, _), run in source.items() if run_arm == arm]


def summarize(runs: list[dict[str, Any]], questions: dict[str, Any]) -> dict[str, Any]:
    outcomes = [bool(passes(score_item(questions[run["question_id"]], run))) for run in runs]
    latencies = [float(run["timing"]["adapter_elapsed_seconds"]) for run in runs]
    by_question: dict[str, list[bool]] = {}
    for run, outcome in zip(runs, outcomes):
        by_question.setdefault(run["question_id"], []).append(outcome)
    usage = [run.get("usage") or {} for run in runs]
    return {
        "passed": sum(outcomes),
        "trials": len(runs),
        "pass_at_3": sum(any(values) for values in by_question.values()),
        "strict": sum(all(values) for values in by_question.values()),
        "questions": len(by_question),
        "input": sum(float(item.get("input_tokens") or 0) for item in usage),
        "output": sum(float(item.get("output_tokens") or 0) for item in usage),
        "cost": sum(estimated_cost(run) for run in runs),
        "latencies": latencies,
        "median": percentile(latencies, 0.5) or 0.0,
        "p95": percentile(latencies, 0.95) or 0.0,
        "mcp": sum(mcp_call_count(run) for run in runs) / len(runs),
        "gold": sum(gold_mcp_calls(questions[run["question_id"]]) for run in runs) / len(runs),
    }


def merge(parts: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [value for part in parts for value in part["latencies"]]
    trials = sum(part["trials"] for part in parts)
    return {
        "passed": sum(part["passed"] for part in parts),
        "trials": trials,
        "pass_at_3": sum(part["pass_at_3"] for part in parts),
        "strict": sum(part["strict"] for part in parts),
        "questions": sum(part["questions"] for part in parts),
        "input": sum(part["input"] for part in parts),
        "output": sum(part["output"] for part in parts),
        "cost": sum(part["cost"] for part in parts),
        "latencies": latencies,
        "median": percentile(latencies, 0.5) or 0.0,
        "p95": percentile(latencies, 0.95) or 0.0,
        "mcp": sum(part["mcp"] * part["trials"] for part in parts) / trials,
        "gold": sum(part["gold"] * part["trials"] for part in parts) / trials,
    }


def pct(part: dict[str, Any]) -> float:
    return 100 * part["passed"] / part["trials"]


def rate(part: dict[str, Any]) -> str:
    return f"{part['passed']}/{part['trials']} ({pct(part):.1f}%)"


def chain(*values: str) -> str:
    return " → ".join(values)


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def grouped_bars(
    destination: Path,
    title: str,
    groups: list[str],
    series: dict[str, list[float]],
    *,
    unit: str = "",
    value_format: str = "{:.0f}",
    y_max: float | None = None,
    reference: tuple[str, list[float]] | None = None,
) -> None:
    """Write a grouped bar chart as a standalone SVG with no dependencies.

    A group label may contain a newline; each line is drawn separately.
    """
    width, height = 1200, 440
    left, right, top, bottom = 70, 24, 56, 110
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_values = [value for values in series.values() for value in values]
    if reference:
        all_values += reference[1]
    top_value = y_max if y_max is not None else max(all_values) * 1.15
    if top_value <= 0:
        top_value = 1.0

    def y_for(value: float) -> float:
        return top + plot_h - (value / top_value) * plot_h

    group_w = plot_w / len(groups)
    bar_w = group_w * 0.72 / len(series)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        f'<text x="{left}" y="30" font-size="18" font-weight="600" fill="#111827">{escape(title)}</text>',
    ]
    ticks = 5
    for index in range(ticks + 1):
        value = top_value * index / ticks
        y = y_for(value)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="#E5E7EB" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" fill="#6B7280" '
            f'text-anchor="end">{value_format.format(value)}{unit}</text>'
        )
    for g_index, group in enumerate(groups):
        base_x = left + g_index * group_w + group_w * 0.14
        for s_index, (name, values) in enumerate(series.items()):
            value = values[g_index]
            x = base_x + s_index * bar_w
            y = y_for(value)
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 3:.1f}" '
                f'height="{top + plot_h - y:.1f}" fill="{COLORS[name]}" rx="2"/>'
            )
            parts.append(
                f'<text x="{x + (bar_w - 3) / 2:.1f}" y="{y - 4:.1f}" font-size="10" '
                f'fill="#374151" text-anchor="middle">{value_format.format(value)}</text>'
            )
        if reference:
            ref_value = reference[1][g_index]
            y = y_for(ref_value)
            x1 = left + g_index * group_w + group_w * 0.08
            x2 = left + (g_index + 1) * group_w - group_w * 0.08
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
                f'stroke="#DC2626" stroke-width="2" stroke-dasharray="6 4"/>'
            )
        label_x = left + g_index * group_w + group_w / 2
        for l_index, line in enumerate(group.split("\n")):
            label_y = top + plot_h + 18 + 14 * l_index
            parts.append(
                f'<text x="{label_x:.1f}" y="{label_y}" font-size="11" fill="#374151" '
                f'text-anchor="middle">{escape(line)}</text>'
            )
    parts.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" '
        f'stroke="#9CA3AF" stroke-width="1"/>'
    )
    legend_x = left
    legend_y = height - 28
    for name in series:
        parts.append(
            f'<rect x="{legend_x}" y="{legend_y - 10}" width="14" height="14" '
            f'fill="{COLORS[name]}" rx="2"/>'
        )
        parts.append(
            f'<text x="{legend_x + 20}" y="{legend_y + 1}" font-size="12" fill="#374151">{escape(name)}</text>'
        )
        legend_x += 30 + 8 * len(name)
    if reference:
        parts.append(
            f'<line x1="{legend_x}" y1="{legend_y - 3}" x2="{legend_x + 22}" y2="{legend_y - 3}" '
            f'stroke="#DC2626" stroke-width="2" stroke-dasharray="6 4"/>'
        )
        parts.append(
            f'<text x="{legend_x + 28}" y="{legend_y + 1}" font-size="12" fill="#374151">{escape(reference[0])}</text>'
        )
    parts.append("</svg>")
    destination.write_text("\n".join(parts) + "\n")


def skill_sizes() -> list[list[str]]:
    rows = []
    for server in ("linear", "slack"):
        index = PROJECT / "skills" / server / "SKILL.md"
        references = sorted((PROJECT / "skills" / server / "references").glob("*.md"))
        index_text = index.read_text()
        reference_bytes = sum(len(path.read_bytes()) for path in references)
        reference_lines = sum(len(path.read_text().splitlines()) for path in references)
        rows.append(
            [
                SERVER_LABEL[server],
                f"{len(index_text.splitlines())} lines, {len(index_text.encode()) / 1024:.1f} KB",
                f"{len(references)} files, {reference_lines} lines, {reference_bytes / 1024:.1f} KB",
            ]
        )
    return rows


def reference_read_rate(runs: list[dict[str, Any]]) -> float:
    reads = 0
    for run in runs:
        if any(
            call.get("source") == "builtin"
            and "/references/" in json.dumps(call.get("arguments", {}))
            for call in run["tool_calls"]
        ):
            reads += 1
    return reads / len(runs)


def question_movers(
    experiment: str,
    questions: dict[str, Any],
    order: list[str],
    runs_by_key: dict[str, tuple[dict, dict]],
) -> list[list[str]]:
    rows = []
    for qid in order:
        skill_total = base_total = 0
        for baseline, skill in runs_by_key.values():
            for attempt in (1, 2, 3):
                base_total += bool(passes(score_item(questions[qid], baseline[("baseline", qid, attempt)])))
                skill_total += bool(passes(score_item(questions[qid], skill[("treatment", qid, attempt)])))
        attempts = 3 * len(runs_by_key)
        rows.append(
            [
                qid,
                questions[qid]["class"],
                f"{base_total}/{attempts}",
                f"{skill_total}/{attempts}",
                f"{skill_total - base_total:+d}",
                skill_total - base_total,
            ]
        )
    return rows


def main() -> None:
    config = json.loads((ROOT / "model_sweep.json").read_text())
    models = config["models"]
    keys = [model["key"] for model in models]
    FIGURES.mkdir(parents=True, exist_ok=True)

    questions: dict[str, dict[str, Any]] = {}
    order: dict[str, list[str]] = {}
    runs: dict[tuple[str, str], tuple[dict, dict]] = {}
    summary: dict[tuple[str, str, str], dict[str, Any]] = {}
    reference_reads: dict[str, float] = {}
    for experiment in EXPERIMENTS:
        rows = read_jsonl(load_experiment(experiment).questions)
        questions[experiment] = {row["id"]: row for row in rows}
        order[experiment] = [row["id"] for row in rows]
        new_runs: list[dict[str, Any]] = []
        for key in keys:
            v1 = load_runs(experiment, key)
            v2 = load_runs(experiment, f"{key}-{V2_SUFFIX}")
            runs[(experiment, key)] = (v1, v2)
            for label, version, arm in ARMS:
                selected = arm_runs(v1, v2, version, arm)
                summary[(experiment, key, label)] = summarize(selected, questions[experiment])
            new_runs += arm_runs(v1, v2, "v2", "treatment")
        reference_reads[experiment] = reference_read_rate(new_runs)

    per_server = {
        (experiment, label): merge([summary[(experiment, key, label)] for key in keys])
        for experiment in EXPERIMENTS
        for label, _, _ in ARMS
    }
    overall = {
        label: merge([per_server[(experiment, label)] for experiment in EXPERIMENTS])
        for label, _, _ in ARMS
    }
    labels = [label for label, _, _ in ARMS]

    # Figures.
    groups = [f"{SERVER_LABEL[experiment]}\n{key}" for experiment in EXPERIMENTS for key in keys]
    grouped_bars(
        FIGURES / "accuracy.svg",
        "Trial pass rate by server and model setting",
        groups,
        {label: [pct(summary[(e, k, label)]) for e in EXPERIMENTS for k in keys] for label in labels},
        unit="%",
        value_format="{:.0f}",
        y_max=115,
    )
    grouped_bars(
        FIGURES / "cost.svg",
        "Estimated list-price cost per trial (USD)",
        groups,
        {
            label: [summary[(e, k, label)]["cost"] / summary[(e, k, label)]["trials"] for e in EXPERIMENTS for k in keys]
            for label in labels
        },
        value_format="{:.2f}",
    )
    grouped_bars(
        FIGURES / "latency_median.svg",
        "Median end-to-end latency (seconds)",
        groups,
        {label: [summary[(e, k, label)]["median"] for e in EXPERIMENTS for k in keys] for label in labels},
        unit="s",
        value_format="{:.0f}",
    )
    grouped_bars(
        FIGURES / "latency_p95.svg",
        "p95 end-to-end latency (seconds)",
        groups,
        {label: [summary[(e, k, label)]["p95"] for e in EXPERIMENTS for k in keys] for label in labels},
        unit="s",
        value_format="{:.0f}",
    )
    grouped_bars(
        FIGURES / "mcp_calls.svg",
        "Mean MCP calls per trial (dashed line is the shortest gold path)",
        groups,
        {label: [summary[(e, k, label)]["mcp"] for e in EXPERIMENTS for k in keys] for label in labels},
        value_format="{:.2f}",
        reference=("gold", [summary[(e, k, "no skill")]["gold"] for e in EXPERIMENTS for k in keys]),
    )
    overall_groups = ["Linear\n342 trials per arm", "Slack\n378 trials per arm", "Both servers\n720 trials per arm"]
    grouped_bars(
        FIGURES / "overall_accuracy.svg",
        "Trial pass rate per arm",
        overall_groups,
        {
            label: [pct(per_server[("linear", label)]), pct(per_server[("slack", label)]), pct(overall[label])]
            for label in labels
        },
        unit="%",
        value_format="{:.1f}",
        y_max=110,
    )
    grouped_bars(
        FIGURES / "overall_cost.svg",
        "Estimated list-price cost per arm (USD)",
        overall_groups,
        {
            label: [
                per_server[("linear", label)]["cost"],
                per_server[("slack", label)]["cost"],
                overall[label]["cost"],
            ]
            for label in labels
        },
        value_format="{:.2f}",
    )

    no_skill = overall["no skill"]
    with_skill = overall["with skill"]

    cheaper = sum(
        summary[(e, k, "with skill")]["cost"] < summary[(e, k, "no skill")]["cost"]
        for e in EXPERIMENTS
        for k in keys
    )
    fewer_calls = sum(
        summary[(e, k, "with skill")]["mcp"] < summary[(e, k, "no skill")]["mcp"]
        for e in EXPERIMENTS
        for k in keys
    )
    p95_better = sum(
        summary[(e, k, "with skill")]["p95"] < summary[(e, k, "no skill")]["p95"]
        for e in EXPERIMENTS
        for k in keys
    )
    median_better = sum(
        summary[(e, k, "with skill")]["median"] < summary[(e, k, "no skill")]["median"]
        for e in EXPERIMENTS
        for k in keys
    )
    linear_up = [k for k in keys if summary[("linear", k, "with skill")]["passed"] > summary[("linear", k, "no skill")]["passed"]]
    slack_up = [k for k in keys if summary[("slack", k, "with skill")]["passed"] > summary[("slack", k, "no skill")]["passed"]]
    slack_down = [k for k in keys if summary[("slack", k, "with skill")]["passed"] < summary[("slack", k, "no skill")]["passed"]]

    lines: list[str] = [
        "# Final results: MCP skills for Linear and Slack",
        "",
        "This document is the single entry point for the benchmark's conclusions. It",
        "covers two arms over the same 40 questions, six Claude settings, and three",
        "attempts each:",
        "",
        "- **No skill.** The agent sees only the MCP tool roster.",
        "- **With skill.** A short `SKILL.md` index plus `references/` files that the",
        "  agent reads only for the object it has already chosen.",
        "",
        "Everything below is generated from the saved trajectories by",
        "`eval/scripts/final_results.py`. Detailed reports and figures are linked",
        "at the end.",
        "",
        "## Summary",
        "",
    ]
    lines += table(
        ["Metric (all 720 trials per arm)", "No skill", "With skill"],
        [
            ["Trial pass rate", rate(no_skill), f"**{rate(with_skill)}**"],
            [
                "Pass@3 (questions with at least one pass, of 240)",
                f"{no_skill['pass_at_3']}/{no_skill['questions']}",
                f"**{with_skill['pass_at_3']}/{with_skill['questions']}**",
            ],
            [
                "Strict reliability (all three attempts pass, of 240)",
                f"{no_skill['strict']}/{no_skill['questions']}",
                f"**{with_skill['strict']}/{with_skill['questions']}**",
            ],
            [
                "Estimated list-price cost, whole arm",
                f"${no_skill['cost']:.2f}",
                f"**${with_skill['cost']:.2f}**",
            ],
            [
                "Mean input tokens per trial",
                f"{no_skill['input'] / no_skill['trials'] / 1000:.1f}k",
                f"**{with_skill['input'] / with_skill['trials'] / 1000:.1f}k**",
            ],
            [
                "Mean output tokens per trial",
                f"{no_skill['output'] / no_skill['trials'] / 1000:.2f}k",
                f"{with_skill['output'] / with_skill['trials'] / 1000:.2f}k",
            ],
            ["Median latency", f"{no_skill['median']:.1f}s", f"{with_skill['median']:.1f}s"],
            ["p95 latency", f"{no_skill['p95']:.1f}s", f"**{with_skill['p95']:.1f}s**"],
            [
                "Mean MCP calls per trial (gold 1.12)",
                f"{no_skill['mcp']:.2f}",
                f"**{with_skill['mcp']:.2f}**",
            ],
        ],
    )
    lines += [
        "![Trial pass rate per arm](eval/results/figures/overall_accuracy.svg)",
        "",
        "![Cost per arm](eval/results/figures/overall_cost.svg)",
        "",
        "Per server:",
        "",
    ]
    lines += table(
        ["Server", "No skill", "With skill", "Change"],
        [
            [
                "Linear",
                rate(per_server[("linear", "no skill")]),
                rate(per_server[("linear", "with skill")]),
                f"{pct(per_server[('linear', 'with skill')]) - pct(per_server[('linear', 'no skill')]):+.1f} pp",
            ],
            [
                "Slack",
                rate(per_server[("slack", "no skill")]),
                rate(per_server[("slack", "with skill")]),
                f"{pct(per_server[('slack', 'with skill')]) - pct(per_server[('slack', 'no skill')]):+.1f} pp",
            ],
        ],
    )
    lines += [
        "## The skill",
        "",
        "Each skill is a short index the agent can keep in view, plus reference",
        "files it opens only after the index has chosen an object.",
        "",
    ]
    lines += table(
        ["Server", "Index (`SKILL.md`)", "References (read on demand)"],
        skill_sizes(),
    )
    lines += [
        "```mermaid",
        "flowchart LR",
        "  prompt[Prompt: read the project skill]",
        "  index[SKILL.md index chooses the object]",
        "  ref[One references file for that object]",
        "  mcp[Single MCP call]",
        "  prompt --> index --> ref --> mcp",
        "```",
        "",
        "The agent opened at least one `references/` file in "
        f"{100 * reference_reads['linear']:.0f}% of Linear trials and "
        f"{100 * reference_reads['slack']:.0f}% of Slack trials. The rest answered from the "
        "index alone.",
        "",
        "## Accuracy",
        "",
        "![Trial pass rate by configuration](eval/results/figures/accuracy.svg)",
        "",
        f"- On Linear, the skill improves {len(linear_up)} of 6 settings"
        + (f" ({', '.join(linear_up)})." if linear_up else "."),
        f"- On Slack, the skill improves {', '.join(slack_up) or 'no setting'} and falls for "
        f"{', '.join(slack_down) or 'no setting'}.",
        "- The Slack no-skill baseline is already near ceiling for Opus and Fable, so",
        "  the index has less to add there. The per-question table below shows",
        "  which Slack questions account for the losses.",
        "- Opus 4.8 with the Linear skill reaches "
        f"{rate(summary[('linear', 'opus-4-8-high', 'with skill')])} at high effort and "
        f"{rate(summary[('linear', 'opus-4-8-medium', 'with skill')])} at medium.",
        "",
        "## Cost",
        "",
        "![Cost per trial](eval/results/figures/cost.svg)",
        "",
        f"- The skill is cheaper than no skill in {cheaper} of 12 server and model settings.",
        f"- Whole-benchmark cost is ${with_skill['cost']:.2f} with the skill and "
        f"${no_skill['cost']:.2f} without it.",
        "- The index stays small. A reference file is loaded only for the object",
        "  the index has already chosen.",
        "",
        "## Latency",
        "",
        "![Median latency](eval/results/figures/latency_median.svg)",
        "",
        "![p95 latency](eval/results/figures/latency_p95.svg)",
        "",
        f"- p95 latency is lower with the skill in {p95_better} of 12 settings. The long",
        "  tail shortens because there are fewer wrong-tool detours.",
        f"- Median latency is lower with the skill in {median_better} of 12 settings.",
        "- The replay proxy is local, so these are harness timings, not live API",
        "  latencies.",
        "",
        "## MCP calls",
        "",
        "![MCP calls versus gold](eval/results/figures/mcp_calls.svg)",
        "",
        f"- The skill makes fewer MCP calls than no skill in {fewer_calls} of 12 settings",
        "  and moves closer to the shortest gold path. Skill-file reads are not MCP",
        "  calls and are excluded.",
        "",
        "## Headline table",
        "",
        "Each cell reads no skill, then with skill.",
        "",
    ]
    headline = []
    for key in keys:
        for experiment in EXPERIMENTS:
            parts = [summary[(experiment, key, label)] for label in labels]
            headline.append(
                [
                    SERVER_LABEL[experiment],
                    key,
                    chain(*(rate(part) for part in parts)),
                    chain(*(f"{part['pass_at_3']}/{part['questions']}" for part in parts)),
                    chain(*(f"{part['strict']}/{part['questions']}" for part in parts)),
                    chain(*(f"{part['input'] / part['trials'] / 1000:.1f}k" for part in parts)),
                    chain(*(f"{part['output'] / part['trials'] / 1000:.2f}k" for part in parts)),
                    chain(*(f"${part['cost'] / part['trials']:.3f}" for part in parts)),
                    chain(*(f"{part['median']:.1f}s" for part in parts)),
                    chain(*(f"{part['p95']:.1f}s" for part in parts)),
                    f"{parts[0]['gold']:.2f}; " + chain(*(f"{part['mcp']:.2f}" for part in parts)),
                ]
            )
    lines += table(
        [
            "Server",
            "Model / effort",
            "Trial pass",
            "Pass@3",
            "Strict reliability",
            "Mean input tokens",
            "Mean output tokens",
            "Estimated cost/trial",
            "Median latency",
            "p95 latency",
            "MCP calls (gold; arms)",
        ],
        headline,
    )
    lines += [
        "## Questions that moved",
        "",
        "Passing attempts summed over all six settings (18 attempts per question per",
        "arm). Positive change means the skill passed more often than no skill.",
        "",
    ]
    for experiment in EXPERIMENTS:
        movers = question_movers(
            experiment,
            questions[experiment],
            order[experiment],
            {key: runs[(experiment, key)] for key in keys},
        )
        changed = [row for row in movers if row[-1] != 0]
        changed.sort(key=lambda row: (-abs(row[-1]), row[0]))
        lines.append(f"### {SERVER_LABEL[experiment]}")
        lines.append("")
        if changed:
            lines += table(
                ["Question", "Class", "No skill", "With skill", "Change"],
                [row[:-1] for row in changed],
            )
        else:
            lines += ["No question changed.", ""]
    lines += [
        "## Method in brief",
        "",
        "```mermaid",
        "flowchart TB",
        "  bank[Frozen question bank with gold tool paths]",
        "  ws[Fresh temporary workspace per trial]",
        "  base[No skill arm: empty workspace]",
        "  treat[Skill arm: .cursor/skills/server/ installed]",
        "  proxy[Record and replay MCP proxy]",
        "  score[Deterministic scoring of tools, order, arguments, policy]",
        "  judge[Blind Opus 4.8 judge for facts and goal]",
        "  gate[Pass gate]",
        "  bank --> ws",
        "  ws --> base",
        "  ws --> treat",
        "  base --> proxy",
        "  treat --> proxy",
        "  proxy --> score",
        "  proxy --> judge",
        "  score --> gate",
        "  judge --> gate",
        "```",
        "",
        "- Six pinned settings: Sonnet 4.6, Opus 4.8, and Fable 5, each at medium and",
        "  high effort, three attempts per question and arm.",
        "- 19 Linear and 21 Slack questions built around confusable tools: planning",
        "  levels, document versus documentation, comments versus review threads,",
        "  search versus history versus thread, send versus draft versus schedule,",
        "  missing capabilities, and destructive confirmations.",
        "- A trial passes only when tool discoverability, sequence, security policy,",
        "  and goal effectiveness are all 1, factual correctness is at least 0.5, and",
        "  execution efficiency is at least 0.7. See `eval/RUBRIC.md`.",
        "- Cost uses Cursor list prices checked on 17 September 2026 and excludes the",
        "  judge. Latency is adapter wall-clock time.",
        "- The with-skill arm was measured on 29 September 2026. The no-skill arm",
        "  does not load a skill, so the 17 September no-skill runs are reused.",
        "",
        "## Limitations",
        "",
        "- Three attempts per cell. Single-question movements of one attempt are",
        "  within noise; read the pooled rows first.",
        "- The with-skill runs and the no-skill runs are 12 days apart. Model",
        "  behavior behind a pinned id can drift; the no-skill arm was not rerun.",
        "- Two pass dimensions are model-judged.",
        "- The bank concentrates on confusable tools and is not a sample of everyday",
        "  MCP traffic.",
        "- Replay removes live service latency and data drift.",
        "",
        "## Artifacts",
        "",
    ]
    lines += table(
        ["Artifact", "Path"],
        [
            ["Comparison", "[eval/results/comparison/SKILL_COMPARISON.md](eval/results/comparison/SKILL_COMPARISON.md)"],
            ["Comparison workbook", "[eval/results/comparison/SKILL_COMPARISON.xlsx](eval/results/comparison/SKILL_COMPARISON.xlsx)"],
            ["Figures", "[eval/results/figures/](eval/results/figures/)"],
            ["Historical unpinned run", "[eval/results/historical/RESULTS.md](eval/results/historical/RESULTS.md)"],
            ["Skills", "[skills/linear/](skills/linear/), [skills/slack/](skills/slack/)"],
            ["No-skill trajectories", "`eval/experiments/<server>/model-runs/<setting>/baseline/`"],
            ["With-skill trajectories", "`eval/experiments/<server>/model-runs/<setting>-v2/treatment/`"],
            ["Gold questions", "[eval/experiments/linear/questions.jsonl](eval/experiments/linear/questions.jsonl), [eval/experiments/slack/questions.jsonl](eval/experiments/slack/questions.jsonl)"],
            ["Rubric", "[eval/RUBRIC.md](eval/RUBRIC.md)"],
        ],
    )
    DESTINATION.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Wrote {DESTINATION}")
    for path in sorted(FIGURES.glob("*.svg")):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
