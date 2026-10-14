# Slack experiment

This experiment compares:

- baseline: Slack replay MCP only;
- treatment: the identical replay MCP plus the native project skill copied from
  `skills/slack/`.

The with-skill arm installs `skills/slack/`. Those trajectories are in `model-runs/<setting>-v2/treatment/` and do not overwrite `model-runs/<setting>/`.

Linear tools, recordings, fixtures, and skill text are absent.

## Order of operations

```bash
python3 eval/scripts/validate_bank.py --experiment slack
python3 eval/scripts/validate_cache.py --experiment slack
python3 eval/scripts/render_review.py --experiment slack

# After all 21 review_status fields are approved:
python3 eval/scripts/validate_bank.py --experiment slack --require-reviewed
python3 eval/scripts/freeze.py --experiment slack

# Requires CURSOR_API_KEY:
.venv/bin/python eval/scripts/probe_native.py --experiment slack
.venv/bin/python eval/scripts/run_eval.py --experiment slack --pilot --attempts 3
.venv/bin/python eval/scripts/judge.py --experiment slack
python3 eval/scripts/report.py --experiment slack \
  > eval/experiments/slack/report.json
```

Do not run the full 21-item bank until the native-skill discovery probe and the
six-item pilot both succeed.

The live/replay check is recorded in `PARITY.md`. Write calls never leave the replay
proxy; they return synthetic results.

## Historical unpinned run

The numbers below are the initial 2026-09-16 unpinned run and are retained for
provenance. They are superseded by the corrected six-configuration timed sweep
under `model-runs/`; use [`FINAL_RESULTS.md`](../../../FINAL_RESULTS.md) and
[`../../results/`](../../results/README.md) for current conclusions.

This run had 126 judged trials, with zero isolation violations and 19 replay cache
misses (almost all `slack_read_user_profile` on member IDs).

- Overall trial pass rate: baseline 35/63 (55.6%), treatment 48/63 (76.2%).
- Pass@3: baseline 13/21, treatment 16/21.
- Strict reliability: baseline 10/21, treatment 16/21.
- Mean tokens per trial: baseline 291,865, treatment 82,269 (71.8% lower).
- Treatment read the native skill in all 63 trials.
- Remaining risk: canvas-update, draft, schedule, upload, and member-listing
  overlap items still fail treatment Pass@3. Capability-gap and thread-reply
  items are the clear skill wins.

Machine-readable results are in `report.json`.
