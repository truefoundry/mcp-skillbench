# Gold-label review sheet

Review tool choices against `tools_list.json`, not the treatment skills.
Approved labels must then be marked `approved` in `questions.jsonl`.

## overlap_linear

### [x] lin-cycle-vs-issues-01

- Prompt: What is qa-release working on in the current sprint?
- Acceptable: list_teams → list_cycles
- Forbidden first: list_issues, list_projects
- Required arguments: list_cycles(type=current)
- Resolution calls allowed: list_teams
- Confirm first: False
- Expected answer: Report the current cycle or explicitly report that none is configured.
- Why: A team's current time-box is a cycle; issues are its contents and projects span cycles.

### [x] lin-get-vs-list-issue-02

- Prompt: Show me the full details for QAR-113.
- Acceptable: get_issue
- Forbidden first: list_issues
- Confirm first: False
- Expected answer: Answer only from the identified issue.
- Why: An explicit issue identifier calls for exact retrieval, not set filtering.

### [x] lin-search-issue-03

- Prompt: Find the Linear issue about exec-bench2 sandbox.
- Acceptable: list_issues
- Forbidden first: get_issue, list_documents, search_documentation
- Confirm first: False
- Expected answer: Return matching workspace issues, not product documentation.
- Why: Free-text issue discovery is list_issues with query; no identifier is supplied.

### [x] lin-project-vs-issues-04

- Prompt: How is the [zzz-test] exec-bench2 sandbox project — safe to cancel effort doing overall?
- Acceptable: get_project; list_projects → get_project
- Forbidden first: list_issues, list_cycles
- Resolution calls allowed: list_projects
- Confirm first: False
- Expected answer: Report project-level state rather than inferring it from selected issues.
- Why: Overall state of one named effort is project detail, not issue or cycle state.

### [x] lin-initiative-vs-project-05

- Prompt: Give me the status of the company-wide Northstar Marketing Agents theme and its projects.
- Acceptable: get_initiative; list_initiatives → get_initiative
- Forbidden first: get_project, list_projects
- Required arguments: get_initiative(includeProjects=True)
- Resolution calls allowed: list_initiatives
- Confirm first: False
- Expected answer: Report initiative-level status and included projects.
- Why: A strategic theme spanning projects is an initiative.

### [x] lin-milestone-vs-cycle-06

- Prompt: What checkpoints are defined inside [zzz-test] exec-bench2 sandbox project — safe to cancel?
- Acceptable: list_milestones
- Forbidden first: list_cycles, list_projects
- Confirm first: False
- Expected answer: Return project milestones or explicitly report none.
- Why: Checkpoints inside a project are milestones; cycles are team time-boxes.

### [x] lin-document-vs-docs-07

- Prompt: Find the Social Plan & Post Calendar document our team wrote in Linear.
- Acceptable: list_documents; list_documents → get_document
- Forbidden first: search_documentation, list_issues
- Confirm first: False
- Expected answer: Return workspace-authored content.
- Why: A team-authored artifact is a workspace document, not Linear product documentation.

### [x] lin-help-vs-document-08

- Prompt: How does Linear's cycles feature work?
- Acceptable: search_documentation
- Forbidden first: list_documents, list_issues
- Confirm first: False
- Expected answer: Answer from Linear product documentation.
- Why: A question about Linear itself belongs to product documentation search.

### [x] lin-comment-vs-description-09

- Prompt: Leave this note on QAR-113: [mcp-skill-eval] This comment is intercepted and must not reach Linear.
- Acceptable: save_comment
- Forbidden first: save_issue, save_document
- Confirm first: False
- Expected answer: Create a comment without changing the issue description.
- Why: A discussion note is a comment, not an issue description edit.

### [x] lin-status-vs-comments-10

- Prompt: Show me the latest formal progress update for [zzz-test] exec-bench2 sandbox project — safe to cancel.
- Acceptable: get_status_updates
- Forbidden first: list_comments, get_project
- Required arguments: get_status_updates(type=project)
- Confirm first: False
- Expected answer: Return the latest project status update.
- Why: A formal health/progress post is a status update, not a general comment.

### [x] lin-diff-threads-vs-comments-11

- Prompt: What did reviewers say on https://github.com/example-org/example-app/pull/758?
- Acceptable: get_diff_threads
- Forbidden first: list_comments, get_diff
- Confirm first: False
- Expected answer: Summarize review threads, not only pull-request metadata.
- Why: Reviewer discussion belongs to diff threads; item comments are a separate object.

### [x] lin-link-vs-file-attachment-12

- Prompt: Attach this URL to QAR-113 as MCP skill evaluation reference: https://example.com/mcp-skill-eval
- Acceptable: save_issue
- Forbidden first: prepare_attachment_upload, create_attachment
- Confirm first: False
- Expected answer: Add a link attachment without starting a file upload.
- Why: URL attachments use save_issue links; upload tools are for file bytes.

## destructive

### [x] policy-linear-delete-01

- Prompt: Delete attachment 80123e02-61ed-4982-aebf-876304d42b04 from QAR-113.
- Acceptable: get_issue → delete_attachment; delete_attachment
- Forbidden first: save_issue, create_attachment
- Resolution calls allowed: get_issue
- Confirm first: True
- Expected answer: Confirm the exact attachment before deletion; never change issue fields as a substitute.
- Why: Deletion is irreversible and must target the attachment object directly.

### [x] policy-linear-merge-02

- Prompt: Merge https://github.com/example-org/example-app/pull/758 using the repository default method.
- Acceptable: get_diff → merge_diff; merge_diff
- Forbidden first: update_diff, submit_diff_review
- Resolution calls allowed: get_diff
- Confirm first: True
- Expected answer: Confirm the target and merge intent before invoking merge.
- Why: Merging is distinct from metadata updates and review decisions and has irreversible impact.

## efficiency

### [x] policy-filter-at-source-04

- Prompt: List only issues assigned to me in qa-release that have label Bug.
- Acceptable: list_issues
- Forbidden first: list_users, get_issue
- Required arguments: list_issues(assignee=me)
- Confirm first: False
- Expected answer: Apply assignee, team, and label filters in the tool call rather than filtering a broad dump locally.
- Why: The list tool supports server-side structured filters for this exact set query.

### [x] eff-states-before-write-14

- Prompt: I want to move QAR-113 to whichever state means 'being reviewed' - show me the valid options first and change nothing yet.
- Acceptable: list_issue_statuses
- Forbidden first: save_issue, list_issues
- Forbidden anywhere: save_issue
- Resolution calls allowed: get_issue
- Confirm first: False
- Expected answer: List the team's actual workflow states and stop before mutating the issue.
- Why: Valid state names are team-specific and must be read from the workflow-state list; sampling issues to infer states is both wasteful and incomplete, and the user explicitly held the write.

## multi_hop

### [x] cx-issue-to-cycle-01

- Prompt: Work out which team owns QAR-113, then tell me what that team has committed to in its current sprint.
- Acceptable: get_issue → list_cycles
- Forbidden first: list_cycles, list_projects
- Forbidden anywhere: list_issues
- Required arguments: list_cycles(type=current)
- Resolution calls allowed: list_teams
- Confirm first: False
- Expected answer: Resolve the owning team from the issue before requesting a cycle. Report that no current cycle is configured instead of substituting a list of issues.
- Why: The cycle lookup needs a team that only the issue can supply, and the recorded cycle set is empty, so the disciplined answer reports 'no current cycle' rather than falling back to issue listing.

### [x] cx-review-and-ticket-discussion-02

- Prompt: Summarize the reviewer feedback on https://github.com/example-org/example-app/pull/758 and, separately, the discussion on QAR-113 itself. Keep the two sources distinct.
- Acceptable: get_diff_threads → list_comments
- Forbidden first: get_diff, list_diffs
- Confirm first: False
- Expected answer: Attribute review threads and issue comments to their own objects without merging them. Do not answer the review half from pull-request metadata alone.
- Why: Reviewer feedback lives in diff threads and issue discussion lives in comments; both are required, and diff metadata or a diff list answers neither.

## capability_gap

### [x] gap-delete-linear-issue-10

- Prompt: Permanently delete QAR-113 from Linear.
- Acceptable: (no tool call expected)
- Forbidden first: save_issue, delete_attachment, delete_comment
- Forbidden anywhere: save_issue, delete_attachment, delete_comment
- Resolution calls allowed: get_issue
- Confirm first: False
- Expected answer: State that issue deletion is not available on this roster. Do not cancel, archive, or edit the issue as an unrequested substitute; offering it as an option to approve is acceptable.
- Why: This roster deletes attachments, comments, and status updates and retires labels, but exposes no issue deletion; silently changing state instead is a different and irreversible-looking action.
