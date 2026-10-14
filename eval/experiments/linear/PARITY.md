# Linear live/replay parity — 2026-09-16

Four read-only calls were reissued through the connected Linear MCP client before
the scored run.

| Call | Result | Notes |
| --- | --- | --- |
| `get_issue(QAR-113)` | Pass | Identifier, title, state, priority, estimate, labels, team, project, and both attachment IDs match. The replay intentionally redacts the assignee and shortens the description. |
| `list_cycles(teamId=qa-release, type=current)` | Exact pass | Live and replay both return an empty list. |
| `get_diff_threads(PR 758)` | Projected pass | Live remains a superset. Replay deliberately retains three stable review themes and removes identities, links, anchors, and duplicate/stale bot messages. |
| `list_documents("Social Plan & Post Calendar")` | Pass | Document ID, title, project, timestamps, and truncated-content behavior match. Replay sanitizes embedded markup in the final truncated cell. |

No semantic drift affects the gold outcomes. The replay cache remains the scored
ground truth; live data is not passed to either arm.
