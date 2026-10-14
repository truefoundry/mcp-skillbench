# Finding Slack content

Read this after choosing search, channel history, a thread, or a name lookup.

## Search

`slack_search_public` is enough for public messages and files. `slack_search_public_and_private` also covers private channels, DMs, and group DMs, and only after the user agrees.

Modifiers `in:`, `from:`, `before:`, `after:`, `is:thread`, and `has:file` work. Boolean operators and parentheses do not. Split a broad question into focused searches, then read the thread, channel, file, or canvas a result points at.

Search ranking reorders and omits. It is the wrong tool for "what was posted recently in this channel".

## History and threads

`slack_read_channel` returns parent messages only, newest first. A parent's reply count is the cue to read the thread. Time bounds are Slack `ts` values (epoch seconds with a fractional suffix), not ISO dates. The same call reads a DM once you have that conversation's id.

`slack_read_thread` takes the conversation id and the parent message's `ts` as `thread_ts`. A reply's own `ts` does not address the thread.

## Names

Channel tools expect a conversation id (`C…`, `G…`, or `D…`). User tools expect a user id (`U…`). `#name` and a display name are not ids.

`slack_search_channels` resolves a channel name and also answers which channels match a description. `slack_list_user_channels` lists conversations the user belongs to. DMs are included only when `types` contains `im` or `mpim`.

`slack_search_users` matches name, email, or id. Names are not unique. When several match, confirm with `slack_read_user_profile` instead of taking the first. A failed lookup stops the task.
