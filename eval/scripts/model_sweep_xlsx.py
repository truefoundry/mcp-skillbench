"""Export the pinned Claude sweep to a spreadsheet for per-question comparison."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import load_experiment  # noqa: E402
from report import MODEL_PRICING_PER_MILLION, passes, percentile  # noqa: E402
from results_md import failure_reason, mcp_sequence  # noqa: E402
from score import read_jsonl, score_item  # noqa: E402

EXPERIMENTS = ("linear", "slack")
ARMS = (("baseline", "no skill"), ("treatment", "with skill"))
HEADER = PatternFill("solid", fgColor="1F2937")
SUBHEADER = PatternFill("solid", fgColor="E5E7EB")
GOOD = PatternFill("solid", fgColor="D1FAE5")
BAD = PatternFill("solid", fgColor="FEE2E2")
FLAT = PatternFill("solid", fgColor="F3F4F6")


def load(experiment_name: str, key: str) -> dict[str, Any]:
    experiment = load_experiment(experiment_name)
    rows = read_jsonl(experiment.questions)
    runs: dict[tuple[str, str, int], dict[str, Any]] = {}
    for path in (experiment.directory / "model-runs" / key).glob("*/*/*.json"):
        run = json.loads(path.read_text())
        runs[(run["arm"], run["question_id"], run["attempt"])] = run
    return {
        "questions": {row["id"]: row for row in rows},
        "order": [row["id"] for row in rows],
        "runs": runs,
    }


def passed(data: dict[str, Any], arm: str, qid: str, attempt: int) -> bool:
    run = data["runs"][(arm, qid, attempt)]
    return bool(passes(score_item(data["questions"][qid], run)))


def attempts_passed(data: dict[str, Any], arm: str, qid: str) -> int:
    return sum(passed(data, arm, qid, attempt) for attempt in (1, 2, 3))


def gold_mcp_calls(question: dict[str, Any]) -> int:
    gold = question["gold"]
    if gold["must_confirm"] or not gold["primary_tools"]:
        return 0
    return min(len(sequence) for sequence in gold["acceptable_sequences"])


def mcp_call_count(run: dict[str, Any]) -> int:
    return sum(
        call.get("source", "mcp") == "mcp" for call in run["tool_calls"]
    )


def estimated_cost(run: dict[str, Any]) -> float:
    usage = run.get("usage") or {}
    model = run.get("actual_model") or run.get("model") or {}
    pricing = MODEL_PRICING_PER_MILLION[model["id"]]
    input_tokens = usage.get("input_tokens", 0)
    cache_read = usage.get("cache_read_tokens", 0)
    cache_write = usage.get("cache_write_tokens", 0)
    uncached = max(0, input_tokens - cache_read - cache_write)
    return (
        uncached * pricing["input"]
        + cache_write * pricing["cache_write"]
        + cache_read * pricing["cache_read"]
        + usage.get("output_tokens", 0) * pricing["output"]
    ) / 1_000_000


def style_header(sheet, row: int, columns: int) -> None:
    for column in range(1, columns + 1):
        cell = sheet.cell(row=row, column=column)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def set_widths(sheet, widths: list[int]) -> None:
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def main() -> None:
    config = json.loads((ROOT / "model_sweep.json").read_text())
    models = config["models"]
    loaded = {
        (experiment, model["key"]): load(experiment, model["key"])
        for experiment in EXPERIMENTS
        for model in models
    }

    book = Workbook()

    # Sheet 1: per-question matrix, one column pair per model configuration.
    matrix = book.active
    matrix.title = "Per-question matrix"
    matrix.cell(row=1, column=1, value="Server")
    matrix.cell(row=1, column=2, value="Question")
    matrix.cell(row=1, column=3, value="Class")
    column = 4
    for model in models:
        matrix.cell(row=1, column=column, value=model["key"])
        matrix.merge_cells(
            start_row=1, start_column=column, end_row=1, end_column=column + 2
        )
        for offset, label in enumerate(("no skill", "with skill", "delta")):
            cell = matrix.cell(row=2, column=column + offset, value=label)
            cell.font = Font(bold=True)
            cell.fill = SUBHEADER
            cell.alignment = Alignment(horizontal="center")
        column += 3
    style_header(matrix, 1, column - 1)
    for index in (1, 2, 3):
        cell = matrix.cell(row=2, column=index, value=("Server", "Question", "Class")[index - 1])
        cell.font = Font(bold=True)
        cell.fill = SUBHEADER

    row = 3
    for experiment in EXPERIMENTS:
        order = loaded[(experiment, models[0]["key"])]["order"]
        questions = loaded[(experiment, models[0]["key"])]["questions"]
        for qid in order:
            matrix.cell(row=row, column=1, value=experiment)
            matrix.cell(row=row, column=2, value=qid)
            matrix.cell(row=row, column=3, value=questions[qid]["class"])
            column = 4
            for model in models:
                data = loaded[(experiment, model["key"])]
                base = attempts_passed(data, "baseline", qid)
                treatment = attempts_passed(data, "treatment", qid)
                matrix.cell(row=row, column=column, value=base)
                matrix.cell(row=row, column=column + 1, value=treatment)
                delta = matrix.cell(
                    row=row, column=column + 2, value=treatment - base
                )
                delta.fill = (
                    GOOD if treatment > base else BAD if treatment < base else FLAT
                )
                column += 3
            row += 1
    matrix.freeze_panes = "D3"
    matrix.auto_filter.ref = f"A2:{get_column_letter(column - 1)}{row - 1}"
    set_widths(matrix, [8, 34, 16] + [10] * (column - 4))

    # Sheet 2: headline metrics per server and configuration.
    summary = book.create_sheet("Summary")
    summary.append(
        [
            "Server",
            "Model",
            "Effort",
            "Arm",
            "Trials passed",
            "Trials",
            "Trial pass rate",
            "Pass@3",
            "Strict reliability",
            "Questions",
            "Mean input tokens",
            "Mean output tokens",
            "Estimated cost/trial",
            "Median latency (s)",
            "p95 latency (s)",
            "Golden mean MCP calls",
            "Mean MCP calls",
            "Call overhead vs gold",
        ]
    )
    style_header(summary, 1, 18)
    for experiment in EXPERIMENTS:
        for model in models:
            key = model["key"]
            data = loaded[(experiment, key)]
            effort = next(
                parameter["value"]
                for parameter in model["selection"]["params"]
                if parameter["id"] == "effort"
            )
            for arm, label in ARMS:
                outcomes = [
                    passed(data, arm, qid, attempt)
                    for qid in data["order"]
                    for attempt in (1, 2, 3)
                ]
                per_item = [
                    [passed(data, arm, qid, attempt) for attempt in (1, 2, 3)]
                    for qid in data["order"]
                ]
                runs = [
                    data["runs"][(arm, qid, attempt)]
                    for qid in data["order"]
                    for attempt in (1, 2, 3)
                ]
                summary.append(
                    [
                        experiment,
                        model["selection"]["id"],
                        effort,
                        label,
                        sum(outcomes),
                        len(outcomes),
                        round(sum(outcomes) / len(outcomes), 3),
                        sum(any(item) for item in per_item),
                        sum(all(item) for item in per_item),
                        len(per_item),
                        round(
                            sum((run.get("usage") or {}).get("input_tokens", 0) for run in runs)
                            / len(runs)
                        ),
                        round(
                            sum((run.get("usage") or {}).get("output_tokens", 0) for run in runs)
                            / len(runs)
                        ),
                        round(sum(estimated_cost(run) for run in runs) / len(runs), 4),
                        round(
                            percentile(
                                [
                                    run["timing"]["adapter_elapsed_seconds"]
                                    for run in runs
                                ],
                                0.5,
                            ),
                            2,
                        ),
                        round(
                            percentile(
                                [
                                    run["timing"]["adapter_elapsed_seconds"]
                                    for run in runs
                                ],
                                0.95,
                            ),
                            2,
                        ),
                        round(
                            sum(
                                gold_mcp_calls(data["questions"][qid])
                                for qid in data["order"]
                            )
                            / len(data["order"]),
                            2,
                        ),
                        round(
                            sum(mcp_call_count(run) for run in runs)
                            / len(runs),
                            2,
                        ),
                        round(
                            sum(mcp_call_count(run) for run in runs) / len(runs)
                            - sum(
                                gold_mcp_calls(data["questions"][qid])
                                for qid in data["order"]
                            )
                            / len(data["order"]),
                            2,
                        ),
                    ]
                )
    summary.freeze_panes = "A2"
    summary.auto_filter.ref = f"A1:R{summary.max_row}"
    set_widths(
        summary,
        [8, 20, 8, 12, 14, 8, 14, 10, 18, 11, 18, 19, 20, 18, 16, 21, 15, 21],
    )

    # Sheet 3: exact MCP call counts by question and model.
    calls_sheet = book.create_sheet("Tool calls")
    calls_sheet.append(
        ["Server", "Question", "Class", "Golden MCP calls"]
        + [
            f"{model['key']} {arm}"
            for model in models
            for arm in ("no skill", "with skill")
        ]
    )
    style_header(calls_sheet, 1, 4 + 2 * len(models))
    for experiment in EXPERIMENTS:
        first = loaded[(experiment, models[0]["key"])]
        for qid in first["order"]:
            row = [
                experiment,
                qid,
                first["questions"][qid]["class"],
                gold_mcp_calls(first["questions"][qid]),
            ]
            for model in models:
                item = loaded[(experiment, model["key"])]
                for arm in ("baseline", "treatment"):
                    row.append(
                        round(
                            sum(
                                mcp_call_count(item["runs"][(arm, qid, attempt)])
                                for attempt in (1, 2, 3)
                            )
                            / 3,
                            2,
                        )
                    )
            calls_sheet.append(row)
    calls_sheet.freeze_panes = "E2"
    calls_sheet.auto_filter.ref = (
        f"A1:{get_column_letter(calls_sheet.max_column)}{calls_sheet.max_row}"
    )
    set_widths(calls_sheet, [8, 34, 16, 18] + [24] * (2 * len(models)))

    # Sheet 4: question x configuration, with both arms' diagnoses side by side.
    detail = book.create_sheet("Question x model")
    detail.append(
        [
            "Server",
            "Question",
            "Class",
            "Model",
            "Effort",
            "No skill (of 3)",
            "With skill (of 3)",
            "Delta",
            "No skill diagnosis",
            "With skill diagnosis",
        ]
    )
    style_header(detail, 1, 10)
    for experiment in EXPERIMENTS:
        for model in models:
            key = model["key"]
            data = loaded[(experiment, key)]
            effort = next(
                parameter["value"]
                for parameter in model["selection"]["params"]
                if parameter["id"] == "effort"
            )
            for qid in data["order"]:
                base = attempts_passed(data, "baseline", qid)
                treatment = attempts_passed(data, "treatment", qid)
                diagnoses = []
                for arm in ("baseline", "treatment"):
                    failing = [
                        data["runs"][(arm, qid, attempt)]
                        for attempt in (1, 2, 3)
                        if not passed(data, arm, qid, attempt)
                    ]
                    diagnoses.append(
                        failure_reason(data["questions"][qid], failing[0])
                        if failing
                        else "passed"
                    )
                detail.append(
                    [
                        experiment,
                        qid,
                        data["questions"][qid]["class"],
                        model["selection"]["id"],
                        effort,
                        base,
                        treatment,
                        treatment - base,
                        diagnoses[0][:500],
                        diagnoses[1][:500],
                    ]
                )
                cell = detail.cell(row=detail.max_row, column=8)
                cell.fill = (
                    GOOD if treatment > base else BAD if treatment < base else FLAT
                )
    detail.freeze_panes = "C2"
    detail.auto_filter.ref = f"A1:J{detail.max_row}"
    set_widths(detail, [8, 34, 16, 20, 8, 14, 15, 8, 70, 70])

    # Sheet 5: every trial, for pivoting.
    trials = book.create_sheet("All trials")
    trials.append(
        [
            "Server",
            "Question",
            "Class",
            "Model",
            "Effort",
            "Arm",
            "Attempt",
            "Passed",
            "Discoverability",
            "Sequence",
            "Efficiency",
            "Security",
            "Factual",
            "Goal",
            "First tool",
            "MCP sequence",
            "MCP calls",
            "Golden MCP calls",
            "Call overhead vs gold",
            "Diagnosis",
            "Skill read",
            "Confirmation requested",
            "Input tokens",
            "Output tokens",
            "Estimated cost",
            "End-to-end latency (s)",
        ]
    )
    style_header(trials, 1, 26)
    for experiment in EXPERIMENTS:
        for model in models:
            key = model["key"]
            data = loaded[(experiment, key)]
            effort = next(
                parameter["value"]
                for parameter in model["selection"]["params"]
                if parameter["id"] == "effort"
            )
            for qid in data["order"]:
                for arm, label in ARMS:
                    for attempt in (1, 2, 3):
                        run = data["runs"][(arm, qid, attempt)]
                        scored = score_item(data["questions"][qid], run)
                        scores = scored["scores"]
                        calls = [
                            call
                            for call in run["tool_calls"]
                            if call.get("source", "mcp") == "mcp"
                        ]
                        trials.append(
                            [
                                experiment,
                                qid,
                                data["questions"][qid]["class"],
                                model["selection"]["id"],
                                effort,
                                label,
                                attempt,
                                "PASS" if passes(scored) else "FAIL",
                                scores["discoverability"],
                                scores["sequence_adherence"],
                                scores["execution_efficiency"],
                                scores["security_policy"],
                                scores["factual_correctness"],
                                scores["goal_effectiveness"],
                                scored["first_substantive_tool"] or "",
                                mcp_sequence(run),
                                len(calls),
                                gold_mcp_calls(data["questions"][qid]),
                                len(calls)
                                - gold_mcp_calls(data["questions"][qid]),
                                failure_reason(data["questions"][qid], run)[:500],
                                bool(run.get("skill_read")),
                                bool(run.get("confirmation_requested")),
                                (run.get("usage") or {}).get("input_tokens", 0),
                                (run.get("usage") or {}).get("output_tokens", 0),
                                round(estimated_cost(run), 4),
                                (run.get("timing") or {}).get(
                                    "adapter_elapsed_seconds"
                                ),
                            ]
                        )
                        cell = trials.cell(row=trials.max_row, column=8)
                        cell.fill = GOOD if passes(scored) else BAD
    trials.freeze_panes = "C2"
    trials.auto_filter.ref = f"A1:Z{trials.max_row}"
    set_widths(
        trials,
        [8, 34, 16, 20, 8, 12, 9, 9, 14, 10, 11, 10, 9, 8, 24, 60, 10, 18, 20, 70, 11, 12, 13, 14, 14, 20],
    )

    destination = ROOT / "results" / "sweep" / "MODEL_SWEEP_RESULTS.xlsx"
    destination.parent.mkdir(parents=True, exist_ok=True)
    book.save(destination)
    stamp_workbook(destination)
    print(f"Wrote {destination}")
    print(
        f"Sheets: matrix rows={matrix.max_row - 2}, summary rows={summary.max_row - 1}, "
        f"question x model rows={detail.max_row - 1}, trials={trials.max_row - 1}"
    )


def stamp_workbook(path: Path) -> None:
    """Rewrite workbook metadata so repeated exports are byte-identical."""
    import io
    import re
    import zipfile

    fixed = (2026, 9, 29, 0, 0, 0)
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as source, zipfile.ZipFile(
        buffer, "w"
    ) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(
                    rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                    b"2026-09-29T00:00:00Z",
                    data,
                )
            info.date_time = fixed
            target.writestr(info, data)
    path.write_bytes(buffer.getvalue())


if __name__ == "__main__":
    main()
