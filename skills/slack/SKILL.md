---
name: slack-skill
description: Use before any Slack tool call. Chooses search versus history versus thread, send versus draft versus schedule, and message versus canvas versus list versus file.
---

# Slack tool choice

Choose one Slack tool, then stop. After the object is known, read that object's file under `references/` before the call.

## Objects

Message, thread, conversation (public channel, private channel, DM, or group DM), user, file, canvas, list, reaction, emoji.

## Choose

1. Name exactly one object. Where the content lives decides, not a keyword.
2. Read unless the request sends, drafts, schedules, reacts, uploads, or creates or edits a conversation, canvas, or list.
3. A topic with no single place is search. Recent messages in one conversation are channel history. Replies under one parent are a thread. A name is not an id: resolve a channel with channel search and a person with user search before the action.
4. Stop. Search is ranked and visibility-scoped. An empty result can mean "not visible". Say so instead of switching tools. Do not guess an id.

## Contrasts

| If the request is about... | Choose | Not |
| --- | --- | --- |
| Public messages or files by topic | `slack_search_public` | private-inclusive search |
| Private channels or DMs included | `slack_search_public_and_private`, after the user agrees | public-only search |
| Recent messages in one channel or DM | `slack_read_channel` | search |
| Replies under one message | `slack_read_thread` with the parent's `thread_ts` | channel history |
| A channel name, or which channels match a topic | `slack_search_channels` | message search |
| Conversations the user belongs to | `slack_list_user_channels` | channel search |
| A person's name or email | `slack_search_users` | searching their messages |
| Posting now, including a reply | `slack_send_message` | a draft or a scheduled send |
| Text the user will review before it posts | `slack_send_message_draft` | `slack_send_message` |
| Delivery at a future time | `slack_schedule_message` | a draft or an immediate send |
| A lightweight acknowledgment | `slack_add_reaction` | a reply |
| A short communication | `slack_send_message` | a canvas, list, or file |
| Free-form shared prose | canvas tools | a list or a message edit |
| Rows that share fields | list tools | a canvas |
| A binary file | the upload sequence in `references/artifacts.md` | message text |

## Not available

This roster cannot edit or delete a sent message, remove a reaction, cancel a scheduled message, or delete a file, list, or list record. It also has no channel invite, join, leave, archive, pin, bookmark, reminder, or user-group tools. Say so. Do not substitute a nearby tool.

## Writes

A send, draft, schedule, upload, canvas update, or create that the user already specified does not need a second confirmation. Resolve names, then do it. Confirm when the destination, time, audience, or file share was inferred. There is no delete or merge on this roster to confirm.

Private-inclusive search includes private channels and DMs. Use it only after the user agrees to that scope.

## Reference files

- Search, history, threads, channels, users: `references/find.md`
- Send, draft, schedule, reactions: `references/write.md`
- Canvases, lists, file upload: `references/artifacts.md`
