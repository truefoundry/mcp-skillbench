# Server-isolated MCP + skills evaluation

Linear and Slack are evaluated separately. The shared Python scripts are harness
code only; each experiment owns its tool snapshot, bank, fixtures, captures, cache,
native skill, runs, freeze, and report.

`experiments/linear` and `experiments/slack` are both complete;
`experiments/integration-cross` is disabled.

All generated reports live under [`results/`](results/README.md); the headline
document is [`FINAL_RESULTS.md`](../FINAL_RESULTS.md) at the repository root.
[`results/comparison/SKILL_COMPARISON.md`](results/comparison/SKILL_COMPARISON.md)
is the per-question comparison of no skill and with skill. Regenerate both
with `make reproduce-reports`.

The earlier unpinned `auto` run remains archived in
[`results/historical/RESULTS.md`](results/historical/RESULTS.md); it is
superseded for model comparisons because the pinned sweep fixes the Slack
confirmation and replay-fixture defects.

## Safety

The replay proxy never forwards calls. All reads are served from the selected
experiment's cache; every write returns a synthetic success response. Never put
credentials in this repository or recording files.

Every SDK trial runs in a fresh temp workspace. Baseline gets the experiment's MCP
server and an empty workspace. Treatment gets the identical MCP server plus one
native project skill directory copied to `.cursor/skills/<name>/` (`SKILL.md`
plus any `references/`). If an experiment's `skill` points at a single file, that
file is installed as `SKILL.md`. Both arms receive the same built-in `read` tool;
only treatment has a skill to discover.

## Workflow

1. `python3 eval/scripts/validate_bank.py --experiment linear`
2. Review `experiments/linear/REVIEW.md`; set `review_status` to `approved` only
   after checking labels against `experiments/linear/tools.json` and official docs.
3. Capture read-only gold and predicted-trap calls with the connected MCP clients.
   Export each call as JSONL and import it:

   ```bash
   python3 eval/scripts/record.py --experiment linear /path/to/capture.jsonl
   ```

4. Re-run validation with `--experiment linear --require-reviewed`.
5. Smoke-test the replay server:

   ```bash
   printf '%s\n' \
     '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
     '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' |
     python3 eval/proxy/server.py \
       --tools eval/experiments/linear/tools.json \
       --cache eval/experiments/linear/cache
   ```

6. Install the pinned Cursor SDK and provide an API key. The runner defaults to the
   included SDK adapter and creates a fresh temporary workspace/agent per trial:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r eval/requirements.txt
   export CURSOR_API_KEY="..."
   EVAL_MODEL=auto .venv/bin/python eval/scripts/run_eval.py \
     --experiment linear --pilot --attempts 3
   ```

   `--pilot` reads the six IDs from `experiments/linear/config.json`. Do not run the
   full bank until the pilot is judged and reported.

   Use `--command "./another-adapter"` to substitute another runtime while keeping
   the same request/trajectory contract.

7. Blind-judge the completed trajectories, score one trajectory, or aggregate all
   results:

   ```bash
   .venv/bin/python eval/scripts/judge.py --experiment linear
   python3 eval/scripts/score.py --experiment linear \
     eval/experiments/linear/runs/baseline/<id>/1.json
   python3 eval/scripts/report.py --experiment linear \
     > eval/experiments/linear/report.json
   ```

## Cache behavior

Keys are SHA-256 hashes over server, tool, and canonical semantic arguments. Caches
are experiment-scoped, so a response from another server cannot be returned.

Because free-text queries are never reproduced word for word, a recording can also
register as its tool's default with `"default": true` (add `"default_any": true` to
serve argument shapes that skip the selector). On an exact-key miss the proxy serves
that default, so a rephrased search still returns data. Defaults live in
`cache/defaults/` and search tools get one default per `content_types` scope, so a
file/canvas search never receives message results. Both arms hit the same fallback,
so it cannot bias the comparison.

A read miss with no default returns `replay_cache_miss` with `isError: true`. It
invalidates that trial and identifies another gold/trap call to record. Do not
interpret a cache miss as a model failure.

## Gold-label provenance

Gold labels must be derived from:

- frozen live schemas in `tools_list.json`;
- official Linear MCP/product documentation;
- official Slack MCP/product documentation.

Do not expose an experiment's treatment skill to the labeler. Each experiment's
`FREEZE.json` hashes its own skill, schema, bank, fixtures, rubric, and cache.

## Status

Linear and Slack are both complete. The published comparison is 1,440 judged
and timed trajectories: 720 with no skill and 720 with the skill, all with
zero replay misses, zero isolation violations, and zero treatment skill skips.
Overall trial accuracy is 73.2% without a skill and 88.3% with the skill.

See the repository [README](../README.md) for the dataset map, findings, metrics,
and reproduction commands, and [`FINAL_RESULTS.md`](../FINAL_RESULTS.md) for the
headline analysis. The mixed Linear/Slack bank remains disabled under
`experiments/integration-cross`.
