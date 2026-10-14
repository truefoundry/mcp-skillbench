# Contributing

Thanks for improving the benchmark. Issues and pull requests are welcome.

## Setup

Use Python 3.11 or newer.

```bash
make setup
make check
```

`make check` is the required local gate: unit tests, both approved banks, both replay caches, freeze manifests, and the sensitive-data scan. Do not run a paid model sweep in a pull request or in GitHub Actions.

## What to change

- Skills live in `skills/linear/` and `skills/slack/`. Keep `SKILL.md` as the index and put argument detail in `references/`.
- Question banks, fixtures, and replay data live only under `eval/experiments/linear/` and `eval/experiments/slack/`.
- If you change a frozen input, regenerate the matching `FREEZE.json` with `python eval/scripts/freeze.py --experiment <name>` and explain why the published comparison still holds.
- Do not add workspace URLs, employee names, customer names, live Slack permalinks, or credentials. `eval/scripts/scan_sensitive.py` rejects the identifiers this release removed.
- Do not commit unpacked `model-runs/` or probe output. The redacted trajectory archive already lives in `eval/data/`.

## Reports

Report regeneration unpacks the archive described in `DATA.md`. A change to report wording should be produced by the scripts, not by hand-editing generated tables.

## License

By submitting a contribution, you agree that it is licensed under the Apache License 2.0. See `LICENSE`.
