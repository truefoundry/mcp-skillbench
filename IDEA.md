# Intro
Standard MCP exposes only each tool's name, description, and schema. If we pair MCP with skills that carry detailed, per-function documentation, the model gets richer context on what each tool does and when to use it. This should improve MCP server’s performance and tool-selection accuracy — most visibly when several tools have overlapping functionality, where name + schema alone leave the choice ambiguous and the extra detail acts as the tiebreaker.

That pairing already shows up in production-style setups: a skill layer for *how* to work (habits, recipes, when-to-use), plus an MCP server for *live* facts (docs, current syntax). Skills should not dump entire manuals into the prompt. The lift comes from focused, opinionated guardrails at the places models usually fail.

# Outcomes
- Improve tool-selection where overlapping functionality is there
- Especially useful in cases where different MCP servers which do identical tasks like (Slack and WhatsApp)
- Cut trial-and-error / shell thrashing: without skills, agents guess flags, retry failed calls, and burn tokens; with skills they should hit a working path on the first try
- Raise correctness and goal completion, not just “picked a plausible tool”
- Keep security and least-privilege habits (no dangerous shortcuts when two tools would both “work”)
- Improve efficiency: fewer wasted tool calls and less raw JSON dumped into context
- Show that skills are not prompt bloat: if they are written as habits + lookup rules, they can *save* tokens by avoiding exploratory loops

# What skills should carry (beyond name + schema)
MCP already gives the contract. Skills should add the missing operational layer:

1. **When to use which tool** — explicit tie-breakers for overlapping servers (Slack vs WhatsApp: channel vs DM, org vs personal, auditability, attachments, threading, who the recipient actually uses).
2. **Verify before inventing** — inspect live help / docs / MCP knowledge tools before composing a call; never invent parameter names. Pairing skills with a docs MCP is the analog of “gcloud help &lt;subcommand&gt; first.”
3. **Idempotent, non-interactive execution** — no `[y/N]` pauses; check-then-create; flags that keep agents unblocked in sandboxes and CI.
4. **Filter at the source** — push filters and field projection to the API/tool instead of dumping huge payloads and grepping locally (protects the context window).
5. **Confirm before destructive work** — preview candidates, refuse silent batch delete/update even if the user said “just do it.”
6. **Security recipes** — least-privilege identity, no long-lived keys when a safer path exists, resource-scoped permissions instead of project/workspace-wide grants.
7. **On-demand discovery** — an index/catalog so the agent *finds* the right skill (or overlapping server) instead of hallucinating a package or picking the first similar tool. Do not preload every skill.

# Evaluation plan (do not vibe-check)
Use a dual-arm design: **baseline MCP (name + schema only)** vs **MCP + skills**, same model, isolated runs.

- **Isolation:** fresh environment per trial; no leftover credentials, shell history, or cached “I already know this CLI.”
- **Repeats:** several independent attempts per scenario (e.g. Pass@3) so one lucky run doesn’t count as success.
- **Judge the trajectory, not just the final answer:** tool calls, retries, invented flags, payload size, whether the chosen tool was the right one among overlaps.
- **Rubric dimensions to score** (adapted from SkillEvaluator-style evals):
  - Discoverability — found the right skill/server/tool among lookalikes
  - Execution efficiency — no exploratory thrashing or failed speculative calls
  - Factual correctness — parameters and APIs that actually exist
  - Goal effectiveness — the user task actually completed
  - Security / policy — did not take the “works but unsafe” shortcut
- **Must-have scenario class:** overlapping MCP servers (Slack vs WhatsApp, and similar pairs). Skills win if they act as the tiebreaker, not if they only help on unique tools.
- **Other scenario classes worth including:** outdated/hallucinated syntax, unfiltered list dumps, destructive actions, auth/identity shortcuts, “find the official skill/tool for X.”
- Compare overall score and reliability (Pass@k), not anecdotes. If possible, check that lift is consistent across scenarios rather than one outlier.

# Authoring rules (so skills help instead of bloating)
- Write habits where models stumble; do not paste the full API reference.
- Point the agent at MCP/docs/help for current syntax; keep the skill as policy + when-to-use.
- Load or retrieve skills on demand from a catalog; overlapping-tool skills should be the first thing retrieved when the task could hit more than one server.
- Treat “skills vs token cost” as something to measure: efficiency and retries should improve if the skills are doing their job.
