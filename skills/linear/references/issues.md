# Issues, comments, and labels

Read this after choosing an issue, comment, or label.

## Issues

`list_issues` `includeArchived` defaults to true. Pass false when archived issues would change the answer. Most other list tools exclude archived items by default.

`save_issue` takes `assignee`, not `assigneeId`. The value may be an id, name, email, or `me`. Creating requires `team` and either `title` or a `template`.

Relation fields (`blocks`, `blockedBy`, `relatedTo`, `links`) append. Detach with the matching `remove*` field. URL attachments use `links` on `save_issue`, not the file-upload tools.

## Comments

`list_comments` takes exactly one parent. `save_comment` creates a root with `body` and exactly one parent, replies with `parentId`, and updates with `id`. Parent fields are ignored on reply and update.

`delete_comment` cannot delete an anchored inline root. Delete the replies, or resolve that thread.

Review threads on a pull request are not comments. Use the diff tools.

## Labels

Issue, project, and initiative labels are separate. Use the matching `save_*_label`, `retire_*_label`, and `restore_*_label`. Prefer those over the deprecated `create_issue_label` and `create_initiative_label`. Retiring a group cascades to its children; existing assignments stay visible.
