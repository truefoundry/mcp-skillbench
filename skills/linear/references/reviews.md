# Diffs and reviews

Read this after choosing a pull request or its review discussion.

`get_diff` is the pull request record: state, branch, metadata. `get_diff_threads` is what reviewers wrote. Both take `urlOrId`: a Linear review URL, diff slug, pull-request id, Linear identifier, or GitHub pull-request URL. `get_diff_threads` can filter with `resolved` or one `threadId`.

`list_comments` does not return these threads, even when the pull request is linked to an issue.

An inline diff comment needs an anchor the diff surface returned. Do not invent an anchor.

`submit_diff_review` needs a body when requesting changes or leaving a comment. `update_diff` can partially succeed; read the result before assuming every field changed. `merge_diff` needs an explicit instruction to merge.
