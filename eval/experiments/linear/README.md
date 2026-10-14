# Linear experiment

This experiment compares:

- baseline: Linear replay MCP only;
- treatment: the identical replay MCP plus the native project skill copied from
  `skills/linear/`.

The with-skill arm installs `skills/linear/`. Those trajectories are in `model-runs/<setting>-v2/treatment/` and do not overwrite `model-runs/<setting>/`.

Slack tools, recordings, fixtures, and skill text are absent.

## Order of operations

```bash
python3 eval/scripts/validate_bank.py --experiment linear
python3 eval/scripts/validate_cache.py --experiment linear
python3 eval/scripts/render_review.py --experiment linear

# After all 19 review_status fields are approved:
python3 eval/scripts/validate_bank.py --experiment linear --require-reviewed
python3 eval/scripts/freeze.py --experiment linear

# Requires CURSOR_API_KEY:
.venv/bin/python eval/scripts/run_eval.py --experiment linear --pilot --attempts 3
.venv/bin/python eval/scripts/judge.py --experiment linear
python3 eval/scripts/report.py --experiment linear \
  > eval/experiments/linear/report.json
```

Do not run the full 19-item bank until the native-skill discovery probe and the
six-item pilot both succeed.

The live/replay check is recorded in `PARITY.md`. Write calls never leave the replay
proxy; they return synthetic results.

## Historical unpinned run

The numbers below are the initial 2026-09-16 unpinned run and are retained for
provenance. They are superseded by the six-configuration timed sweep under
`model-runs/`; use [`FINAL_RESULTS.md`](../../../FINAL_RESULTS.md) and
[`../../results/`](../../results/README.md) for current conclusions.

This run had 114 judged trials, with zero replay misses and zero isolation
violations.

- Overall trial pass rate: baseline 16/57 (28.1%), treatment 53/57 (93.0%).
- Pass@3: baseline 8/19, treatment 19/19.
- Strict reliability: baseline 3/19, treatment 16/19.
- Mean tokens per trial: baseline 240,550, treatment 81,538 (66.1% lower).
- Treatment read the native skill in all 57 trials.
- Remaining risk: one treatment attempt invoked `merge_diff` without the required
  confirmation, so destructive strict reliability was not perfect.

Machine-readable results are in `report.json`.
