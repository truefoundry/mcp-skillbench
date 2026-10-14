# Benchmark data

The Git checkout contains the inputs, aggregate evidence, and redacted trajectories for this comparative study. There is no GitHub Release.

## What is in Git

- Approved question banks, tool schemas, fixtures, captures, and the replay cache under `eval/experiments/linear/` and `eval/experiments/slack/`.
- Freeze manifests for the current skills (`FREEZE.json`).
- Aggregate Markdown and XLSX reports, plus SVG figures, under `eval/results/`.
- `FINAL_RESULTS.md`, the headline summary.

`eval/experiments/integration-cross/` is a disabled cross-server bank. It is not part of the headline results. `eval/results/historical/` is an earlier unpinned run whose source trajectories were not retained, so it cannot be regenerated.

## Trajectory archive

The redacted trajectories are the file [`eval/data/mcp-skillbench-trajectories-2026-09-29.tar.gz`](eval/data/mcp-skillbench-trajectories-2026-09-29.tar.gz). Its SHA-256 is in [`eval/data/SHA256SUMS`](eval/data/SHA256SUMS), and the layout is described by [`eval/data/trajectories-manifest.json`](eval/data/trajectories-manifest.json).

```bash
make reproduce-reports
```

That checks the checksum and unpacks the archive into `eval/experiments/<linear|slack>/model-runs/`. Those unpacked directories are gitignored. The archive itself stays in Git.

## Provenance and redaction

The published metrics were computed from the frozen private source, commit `95750703808a5ebb8661d07d9dfc57dcb2445e64`, before this public copy was prepared. The archive in Git is a post-run redacted dataset. It is not a claim that the original model calls saw the fictional identifiers.

Redaction replaces workspace URLs, workspace and user identifiers, employee names, customer and project names, pull-request locations, and Slack permalinks with stable fictional values. The same substitutions were applied to the question banks, fixtures, captures, replay cache, and reports that remain in Git. Exact replay-cache filenames were recomputed from the redacted arguments. `FREEZE.json` identifies this public tree.

Probe run sets are omitted from the archive.

## Fixture policy

Fixtures are the stable values substituted into question prompts. They are fictional in this public tree. Do not replace them with live workspace identifiers if you want the committed replay cache to keep answering.

## License and limitations

Benchmark code, skills, reports, and the redacted trajectory archive are released under the Apache License 2.0. See [`LICENSE`](LICENSE).

The archive cannot recreate a live Linear or Slack workspace. It can regenerate the aggregate reports. A new paid sweep can differ from the published numbers because model behavior changes. Three attempts per question is a small sample, and two of the pass checks are model-judged.
