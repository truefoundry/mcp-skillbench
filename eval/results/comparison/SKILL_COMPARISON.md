# No skill compared with the progressive skill

No skill is the saved baseline arm. With skill is the progressive bundle in
`skills/linear/` and `skills/slack/`: a short `SKILL.md` index plus
`references/` files read only for the chosen object. The no-skill arm was
not rerun. The judge, questions, fixtures, and agent prompt match.

Each arrow below is no skill, then with skill. List price is the mean per
trial. Input tokens are the full prompt count. Latency is
`adapter_elapsed_seconds`. MCP counts exclude skill-file reads. Gold is 0
when the question must confirm or has no primary tool, otherwise the shortest
acceptable sequence.

The pivotable workbook is [SKILL_COMPARISON.xlsx](SKILL_COMPARISON.xlsx).

## Headline results

| Server | Model / effort | Trial pass (no skill → with skill) | Pass@3 | Strict reliability | Mean input tokens | Mean output tokens | Estimated cost/trial | Median latency | p95 latency | MCP calls (gold; no skill → with skill) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Linear | sonnet-4-6-medium | 32/57 (56.1%) → 47/57 (82.5%) | 11/19 → 17/19 | 10/19 → 14/19 | 31.2k → 32.7k | 0.99k → 0.90k | $0.041 → $0.049 | 27.8s → 28.1s | 65.7s → 47.6s | 1.00; 2.81 → 1.61 |
| Slack | sonnet-4-6-medium | 47/63 (74.6%) → 53/63 (84.1%) | 18/21 → 19/21 | 12/21 → 16/21 | 45.1k → 33.9k | 1.50k → 1.21k | $0.066 → $0.050 | 30.7s → 29.8s | 94.6s → 64.8s | 1.24; 3.17 → 1.71 |
| Linear | sonnet-4-6-high | 34/57 (59.6%) → 47/57 (82.5%) | 14/19 → 18/19 | 8/19 → 13/19 | 37.0k → 37.0k | 1.36k → 1.08k | $0.053 → $0.055 | 30.8s → 29.4s | 85.8s → 54.6s | 1.00; 3.02 → 1.84 |
| Slack | sonnet-4-6-high | 42/63 (66.7%) → 56/63 (88.9%) | 17/21 → 21/21 | 12/21 → 17/21 | 66.9k → 51.9k | 2.63k → 1.83k | $0.094 → $0.068 | 37.1s → 32.6s | 207.0s → 82.7s | 1.24; 4.70 → 2.54 |
| Linear | opus-4-8-medium | 37/57 (64.9%) → 54/57 (94.7%) | 15/19 → 19/19 | 10/19 → 16/19 | 38.6k → 36.7k | 1.22k → 0.88k | $0.090 → $0.095 | 30.8s → 29.5s | 64.3s → 38.7s | 1.00; 2.00 → 1.16 |
| Slack | opus-4-8-medium | 55/63 (87.3%) → 55/63 (87.3%) | 20/21 → 19/21 | 16/21 → 17/21 | 37.2k → 40.4k | 1.41k → 1.06k | $0.095 → $0.095 | 33.2s → 31.4s | 55.4s → 48.5s | 1.24; 1.83 → 1.27 |
| Linear | opus-4-8-high | 38/57 (66.7%) → 55/57 (96.5%) | 16/19 → 19/19 | 10/19 → 18/19 | 45.2k → 40.2k | 1.56k → 0.97k | $0.112 → $0.098 | 35.1s → 30.4s | 75.6s → 46.4s | 1.00; 2.21 → 1.14 |
| Slack | opus-4-8-high | 56/63 (88.9%) → 55/63 (87.3%) | 19/21 → 19/21 | 18/21 → 18/21 | 41.1k → 40.8k | 1.57k → 1.15k | $0.108 → $0.099 | 36.9s → 32.9s | 65.0s → 50.3s | 1.24; 1.62 → 1.33 |
| Linear | fable-5-medium | 35/57 (61.4%) → 53/57 (93.0%) | 14/19 → 19/19 | 9/19 → 15/19 | 47.9k → 43.6k | 1.31k → 0.91k | $0.174 → $0.162 | 41.2s → 35.5s | 80.8s → 52.8s | 1.00; 2.12 → 1.30 |
| Slack | fable-5-medium | 57/63 (90.5%) → 54/63 (85.7%) | 20/21 → 20/21 | 18/21 → 15/21 | 45.5k → 51.6k | 1.24k → 1.24k | $0.169 → $0.186 | 41.8s → 39.8s | 57.6s → 63.7s | 1.24; 1.86 → 1.68 |
| Linear | fable-5-high | 36/57 (63.2%) → 53/57 (93.0%) | 14/19 → 19/19 | 9/19 → 16/19 | 52.2k → 47.8k | 1.59k → 1.05k | $0.199 → $0.176 | 43.8s → 37.3s | 87.5s → 53.5s | 1.00; 2.30 → 1.32 |
| Slack | fable-5-high | 58/63 (92.1%) → 54/63 (85.7%) | 20/21 → 21/21 | 18/21 → 15/21 | 51.3k → 53.8k | 1.63k → 1.45k | $0.200 → $0.201 | 49.6s → 40.7s | 82.0s → 64.8s | 1.24; 1.97 → 1.71 |

## Reading the result

- Linear trial pass rises from no skill to with skill in 6 of 6 configurations (sonnet-4-6-medium, sonnet-4-6-high, opus-4-8-medium, opus-4-8-high, fable-5-medium, fable-5-high).
- Slack trial pass rises for sonnet-4-6-medium, sonnet-4-6-high and falls for opus-4-8-high, fable-5-medium, fable-5-high.
- Estimated list-price cost per trial is lower with the skill than
  without it in 6 of 12 configurations.
- Mean MCP calls are lower with the skill than without it in
  12 of 12 configurations. Skill-file reads are excluded.
- Compare paired medium and high rows per model. Higher effort is not
  uniformly better.

## Per question

Each cell is attempts passed out of three. With skill is colored in the
workbook when it differs from no skill.

### linear · sonnet-4-6-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 3/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 2/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 0/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 2/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 3/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 3/3 | 3/3 |
| lin-status-vs-comments-10 | overlap_linear | 0/3 | 1/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 3/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 3/3 | 2/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 3/3 | 3/3 |
| policy-filter-at-source-04 | efficiency | 0/3 | 0/3 |
| cx-issue-to-cycle-01 | multi_hop | 0/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 0/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 0/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### linear · sonnet-4-6-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 3/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 3/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 0/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 2/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 2/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 2/3 | 2/3 |
| lin-status-vs-comments-10 | overlap_linear | 0/3 | 1/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 3/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 2/3 | 3/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 3/3 | 2/3 |
| policy-filter-at-source-04 | efficiency | 1/3 | 1/3 |
| cx-issue-to-cycle-01 | multi_hop | 0/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 1/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 2/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### linear · opus-4-8-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 2/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 1/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 3/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 3/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 3/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 3/3 | 2/3 |
| lin-status-vs-comments-10 | overlap_linear | 1/3 | 3/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 3/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 2/3 | 3/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 3/3 | 3/3 |
| policy-filter-at-source-04 | efficiency | 1/3 | 2/3 |
| cx-issue-to-cycle-01 | multi_hop | 2/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 3/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 0/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### linear · opus-4-8-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 3/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 2/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 3/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 3/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 3/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 3/3 | 3/3 |
| lin-status-vs-comments-10 | overlap_linear | 3/3 | 3/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 3/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 2/3 | 3/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 1/3 | 3/3 |
| policy-filter-at-source-04 | efficiency | 1/3 | 1/3 |
| cx-issue-to-cycle-01 | multi_hop | 1/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 3/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 1/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### linear · fable-5-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 2/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 1/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 2/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 3/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 3/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 3/3 | 3/3 |
| lin-status-vs-comments-10 | overlap_linear | 2/3 | 3/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 3/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 2/3 | 3/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 0/3 | 2/3 |
| policy-filter-at-source-04 | efficiency | 3/3 | 2/3 |
| cx-issue-to-cycle-01 | multi_hop | 0/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 2/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 1/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### linear · fable-5-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| lin-cycle-vs-issues-01 | overlap_linear | 0/3 | 2/3 |
| lin-get-vs-list-issue-02 | overlap_linear | 3/3 | 3/3 |
| lin-search-issue-03 | overlap_linear | 3/3 | 3/3 |
| lin-project-vs-issues-04 | overlap_linear | 1/3 | 3/3 |
| lin-initiative-vs-project-05 | overlap_linear | 0/3 | 1/3 |
| lin-milestone-vs-cycle-06 | overlap_linear | 0/3 | 3/3 |
| lin-document-vs-docs-07 | overlap_linear | 3/3 | 3/3 |
| lin-help-vs-document-08 | overlap_linear | 3/3 | 3/3 |
| lin-comment-vs-description-09 | overlap_linear | 3/3 | 3/3 |
| lin-status-vs-comments-10 | overlap_linear | 2/3 | 3/3 |
| lin-diff-threads-vs-comments-11 | overlap_linear | 0/3 | 3/3 |
| lin-link-vs-file-attachment-12 | overlap_linear | 2/3 | 3/3 |
| policy-linear-delete-01 | destructive | 3/3 | 3/3 |
| policy-linear-merge-02 | destructive | 2/3 | 2/3 |
| policy-filter-at-source-04 | efficiency | 3/3 | 3/3 |
| cx-issue-to-cycle-01 | multi_hop | 0/3 | 3/3 |
| cx-review-and-ticket-discussion-02 | multi_hop | 3/3 | 3/3 |
| gap-delete-linear-issue-10 | capability_gap | 2/3 | 3/3 |
| eff-states-before-write-14 | efficiency | 3/3 | 3/3 |

### slack · sonnet-4-6-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 2/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 2/3 | 1/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 0/3 |
| slack-thread-vs-channel-04 | overlap_slack | 0/3 | 0/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 3/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 2/3 | 2/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 3/3 | 3/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 1/3 | 3/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 0/3 | 3/3 |
| gap-edit-sent-message-07 | capability_gap | 0/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 3/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 2/3 | 3/3 |
| eff-projection-channels-13 | efficiency | 2/3 | 2/3 |
| sec-private-then-draft-15 | security | 3/3 | 3/3 |

### slack · sonnet-4-6-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 1/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 0/3 | 3/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 3/3 |
| slack-thread-vs-channel-04 | overlap_slack | 1/3 | 1/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 3/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 1/3 | 3/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 3/3 | 3/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 0/3 | 1/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 1/3 | 2/3 |
| gap-edit-sent-message-07 | capability_gap | 0/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 2/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 0/3 | 1/3 |
| eff-projection-channels-13 | efficiency | 3/3 | 3/3 |
| sec-private-then-draft-15 | security | 3/3 | 3/3 |

### slack · opus-4-8-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 3/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 1/3 | 2/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 3/3 |
| slack-thread-vs-channel-04 | overlap_slack | 2/3 | 2/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 0/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 3/3 | 3/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 3/3 | 3/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 0/3 | 0/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 3/3 | 3/3 |
| gap-edit-sent-message-07 | capability_gap | 3/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 3/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 2/3 | 3/3 |
| eff-projection-channels-13 | efficiency | 3/3 | 3/3 |
| sec-private-then-draft-15 | security | 2/3 | 3/3 |

### slack · opus-4-8-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 3/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 3/3 | 3/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 3/3 |
| slack-thread-vs-channel-04 | overlap_slack | 0/3 | 1/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 0/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 3/3 | 3/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 3/3 | 3/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 0/3 | 0/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 3/3 | 3/3 |
| gap-edit-sent-message-07 | capability_gap | 3/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 3/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 3/3 | 3/3 |
| eff-projection-channels-13 | efficiency | 3/3 | 3/3 |
| sec-private-then-draft-15 | security | 2/3 | 3/3 |

### slack · fable-5-medium

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 3/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 3/3 | 3/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 2/3 |
| slack-thread-vs-channel-04 | overlap_slack | 3/3 | 2/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 3/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 0/3 | 1/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 1/3 | 2/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 2/3 | 0/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 3/3 | 3/3 |
| gap-edit-sent-message-07 | capability_gap | 3/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 3/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 3/3 | 3/3 |
| eff-projection-channels-13 | efficiency | 3/3 | 2/3 |
| sec-private-then-draft-15 | security | 3/3 | 3/3 |

### slack · fable-5-high

| Question | Class | No skill | With skill |
| --- | --- | --- | --- |
| slack-history-vs-search-01 | overlap_slack | 3/3 | 3/3 |
| slack-topic-vs-history-02 | overlap_slack | 3/3 | 3/3 |
| slack-private-search-03 | overlap_slack | 3/3 | 1/3 |
| slack-thread-vs-channel-04 | overlap_slack | 3/3 | 1/3 |
| slack-draft-vs-send-05 | overlap_slack | 3/3 | 3/3 |
| slack-schedule-vs-draft-06 | overlap_slack | 3/3 | 3/3 |
| slack-members-vs-users-07 | overlap_slack | 3/3 | 3/3 |
| slack-my-channels-vs-search-08 | overlap_slack | 3/3 | 3/3 |
| slack-get-vs-add-reaction-09 | overlap_slack | 3/3 | 3/3 |
| slack-list-vs-canvas-10 | overlap_slack | 0/3 | 1/3 |
| slack-canvas-vs-list-11 | overlap_slack | 3/3 | 3/3 |
| slack-upload-vs-message-12 | overlap_slack | 2/3 | 2/3 |
| policy-slack-public-scope-03 | security | 3/3 | 3/3 |
| cx-canvas-read-before-update-04 | multi_hop | 2/3 | 2/3 |
| cx-reply-to-parent-thread-06 | multi_hop | 3/3 | 3/3 |
| gap-edit-sent-message-07 | capability_gap | 3/3 | 3/3 |
| gap-cancel-scheduled-08 | capability_gap | 3/3 | 3/3 |
| gap-remove-reaction-09 | capability_gap | 3/3 | 3/3 |
| amb-shared-doc-object-11 | underspecified | 3/3 | 3/3 |
| eff-projection-channels-13 | efficiency | 3/3 | 2/3 |
| sec-private-then-draft-15 | security | 3/3 | 3/3 |
