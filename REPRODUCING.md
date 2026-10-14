# Reproducing the benchmark

Python 3.11 or newer is required. Three levels are supported. Only the third spends model money.

## 1. Free verification

```bash
make setup
make check
```

This creates `.venv`, installs `cursor-sdk==1.0.31` and `openpyxl==3.1.5`, and then:

- runs the unit tests
- validates both approved question banks
- validates both replay caches
- checks `FREEZE.json` for Linear and Slack
- scans the checkout for known private identifiers and secret patterns

No API key is required. `make check` does not call a model.

## 2. Report regeneration

Unpack the redacted trajectory archive that ships in the repository and rebuild the aggregate reports:

```bash
make reproduce-reports
```

`eval/scripts/fetch_trajectories.py` reads [`eval/data/mcp-skillbench-trajectories-2026-09-29.tar.gz`](eval/data/mcp-skillbench-trajectories-2026-09-29.tar.gz) and refuses it unless its SHA-256 matches [`eval/data/SHA256SUMS`](eval/data/SHA256SUMS). Report commands read saved trajectories only. Nothing is downloaded.

The headline numbers in [`FINAL_RESULTS.md`](FINAL_RESULTS.md) came from the frozen private source. Regeneration checks that this redacted copy still produces those aggregates. `eval/results/historical/` cannot be regenerated. `integration-cross` is disabled and is excluded from the headline.

## 3. Paid rerun

Copy [`.env.example`](.env.example) to `.env` and export `CURSOR_API_KEY`. The account must be able to use the models pinned in [`eval/model_sweep.json`](eval/model_sweep.json). The judge is `claude-opus-4-8` at high effort. The six settings are Sonnet 4.6, Opus 4.8, and Fable 5, each at medium and high effort.

Start with the pilot. Each experiment's `pilot_ids` lists six questions. One attempt and both arms is 24 agent trials across Linear and Slack:

```bash
export CURSOR_API_KEY=...
make pilot
```

A full sweep is much larger. The published measurement is 40 questions, six settings, two arms, and three attempts: 1,440 agent trials, plus judging. Expect a substantial Cursor bill, on the order of the published arm costs in [`FINAL_RESULTS.md`](FINAL_RESULTS.md), before judging. Judging adds more Opus 4.8 calls.

```bash
export CURSOR_API_KEY=...
export CONFIRM=yes
make sweep
```

`make sweep` runs `eval/scripts/run_model_sweep.py --phase all --jobs 4 --retries 3 --skip-existing`. Four workers is the default here so a fresh run is less likely to trip rate limits. The original sweep used 12. If calls are rate-limited, rerun the same command. `--skip-existing` resumes completed trials. To rerun one phase, call the script directly with `--phase trials`, `--phase judge`, or `--phase report`.

Do not point a paid run at a live workspace if you intend to compare with the published replay. The committed cache answers recorded tool calls locally. New argument combinations miss the cache and need a live server, which this repository does not configure.

## Canonical paths

Question banks, fixtures, caches, and new runs belong under `eval/experiments/linear/` and `eval/experiments/slack/`. Root-level copies of those inputs are not part of this release.
