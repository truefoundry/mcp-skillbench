# Slack live/replay parity — 2026-09-16

Four read-only calls were reissued through the connected Slack MCP client before
the scored run.

| Call | Result | Notes |
| --- | --- | --- |
| `slack_read_thread(C0EXAMPLE01, 1788954922.315819, concise)` | Projected pass | Live remains a superset with identities and full quotes. Replay keeps the same parent theme and reply sequence (HF-only verification, protocol cache miss, env override, two Linear issues). |
| `slack_read_canvas(F0EXAMPLE01)` | Pass | Canvas ID and title (`CLI improvements`) match. Live returns the full tables; replay stores a summarized catalog of the same commands and the same API-vs-backend split. |
| `slack_search_public("remote MCP is the direct proxy case" in:mcp-gateway)` | Pass | Channel ID, message timestamp `1789013638.410999`, parent thread `1788954922.315819`, and paraphrase of the remote-MCP/direct-proxy sentence match. Replay redacts the author. |
| `slack_list_user_channels(name_prefix=mcp, names_only)` | Exact pass | Live and replay both return `#mcp-gateway` as the only matching membership. |

No semantic drift affects the gold outcomes. The replay cache remains the scored
ground truth; live data is not passed to either arm.
