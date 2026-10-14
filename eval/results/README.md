# Results

The published comparison is no skill versus the progressive skill in `skills/linear/` and `skills/slack/`. The single entry point is [`FINAL_RESULTS.md`](../../FINAL_RESULTS.md) at the repository root.

| Folder | What it contains |
| --- | --- |
| `comparison/` | Per-question comparison and workbook: `SKILL_COMPARISON.md`, `SKILL_COMPARISON.xlsx`. |
| `figures/` | SVG charts used by the repository README and `FINAL_RESULTS.md`. |
| `historical/` | The first unpinned `auto` run from 16 September 2026. Superseded; kept for provenance. Its source `runs/` directories are not committed, so it cannot be regenerated. |

## Regenerate

These commands read saved trajectories only. None call a model.

```bash
.venv/bin/python eval/scripts/skill_comparison.py
.venv/bin/python eval/scripts/final_results.py
```

`make reproduce-reports` unpacks the trajectory archive and runs both. The workbook needs `openpyxl`.

## Where the trajectories are

The redacted trajectories are `eval/data/mcp-skillbench-trajectories-2026-09-29.tar.gz`. Unpacking installs:

```text
eval/experiments/<linear|slack>/model-runs/<setting>/baseline/
eval/experiments/<linear|slack>/model-runs/<setting>-v2/treatment/
```

`<setting>` is one of `sonnet-4-6-medium`, `sonnet-4-6-high`, `opus-4-8-medium`, `opus-4-8-high`, `fable-5-medium`, and `fable-5-high`, as pinned in [`../model_sweep.json`](../model_sweep.json). The no-skill arm is `baseline/`. The with-skill arm is `treatment/` under the `-v2` directory. See [`DATA.md`](../../DATA.md).
