---
name: linear-app-skill
description: Use before any Linear tool call. Chooses the object and tool, including planning level, document versus documentation, comments versus diff threads, and URL versus file attachments.
---

# Linear tool choice

Choose one Linear tool, then stop. After the object is known, read that object's file under `references/` before the call.

## Objects

Initiative (several projects), project (one effort), milestone (a checkpoint inside one project), cycle (one team's sprint), issue (one piece of work). Also: workspace document, Linear's own help docs, comment, status update, diff, attachment, release, label, notification, template, agent skill, team, user.

## Choose

1. Name exactly one object. Scope decides, not a keyword.
2. Read unless the request creates or changes something.
3. A specific record is `get_*`. A set, filter, or free-text search is `list_*`. A write is that object's `save_*`; an id updates. There is no `search_issues`. Issue search is `list_issues` with `query`.
4. Stop. An empty result means nothing matched. Do not switch object types because the result is empty. If `list_cycles` is empty, no cycle is configured; do not fall back to `list_issues`.

## Contrasts

| If the request is about... | Choose | Not |
| --- | --- | --- |
| An org-wide theme spanning projects | `list_initiatives` / `get_initiative` | projects or issues |
| One named effort and its status | `get_project` / `list_projects` | initiatives or cycles |
| A team's current sprint or time window | `list_cycles` | issues or projects |
| A checkpoint inside one project | `list_milestones` | projects or cycles |
| One task, or a filtered set of tasks | `get_issue` / `list_issues` | initiative, project, or cycle tools |
| Something the workspace wrote | `list_documents` / `get_document` | `search_documentation` |
| How Linear itself works | `search_documentation` | document tools |
| A unit of work | `save_issue` | a document or status update |
| A durable written artifact | `save_document` | an issue or status update |
| A progress note on a project or initiative | `save_status_update` | a document |
| A comment on an issue, project, document, milestone, or update | `list_comments` / `save_comment` | diff threads |
| One pull request's state | `get_diff` | `get_diff_threads` |
| Review discussion on a pull request | `get_diff_threads` | `get_diff` or `list_comments` |
| A URL on an issue | `save_issue` `links` | file-attachment tools |
| A file on an issue | the upload sequence in `references/content.md` | `create_attachment` |

## Not available

This roster cannot delete issues, projects, initiatives, documents, or milestones. Deletes exist for comments, attachments, and status updates. Labels retire and restore. Creating teams or users, and archiving as its own operation, are absent. Say so. Do not substitute a state change for a deletion.

## Writes

Confirm before delete, retire, share or unshare, review submission, diff status changes, and merge. A write the user already specified does not need a second confirmation.

Issue and project tools generally accept a name. Cycle and document filters need an id; resolve the name first. Details are in the reference for that object.

## Reference files

- Cycle, project, milestone, initiative: `references/planning.md`
- Issues, comments, labels: `references/issues.md`
- Documents, help docs, attachments: `references/content.md`
- Diffs and reviews: `references/reviews.md`
