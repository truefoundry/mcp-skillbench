# Sending, drafting, and reactions

Read this after choosing a message write or a reaction.

`slack_send_message` is both a top-level post and a thread reply. A reply sets `thread_ts` to the parent message's `ts`. Replying to a reply still uses that parent `ts`, not the reply's `ts`. A top-level post where a reply belongs notifies the whole channel.

A resolved user id can be `channel_id` for a DM. Do not create a conversation just to obtain a DM. Create a channel or group DM only when the user asks for a new conversation.

`slack_send_message_draft` stores text in Drafts without posting. Only one attached draft is allowed per channel.

`slack_schedule_message` delivers later. The time is a Unix timestamp at least 2 minutes and at most 120 days ahead. It cannot target a Slack Connect channel, and this roster cannot edit or cancel it afterward.

`slack_add_reaction` takes the emoji name without colons (`thumbsup`, not `:thumbsup:`). Resolve a custom emoji with `slack_search_emojis` first. `slack_get_reactions` reads reactions; it does not add one. This roster cannot remove a reaction or edit a sent message.
