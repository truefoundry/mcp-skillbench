"""Classify tool calls that must never reach production during evaluation."""

from __future__ import annotations

from typing import Any


SLACK_WRITES = {
    "slack_add_list_record",
    "slack_add_reaction",
    "slack_complete_file_upload",
    "slack_create_canvas",
    "slack_create_conversation",
    "slack_create_list",
    "slack_get_file_upload_url",
    "slack_schedule_message",
    "slack_send_message",
    "slack_send_message_draft",
    "slack_update_canvas",
    "slack_update_list",
    "slack_update_list_record",
}

LINEAR_WRITE_PREFIXES = (
    "create_",
    "delete_",
    "restore_",
    "retire_",
    "save_",
)

LINEAR_WRITES = {
    "mark_notification",
    "merge_diff",
    "prepare_attachment_upload",
    "resolve_diff_thread",
    "share_issue",
    "submit_diff_review",
    "unshare_issue",
    "update_diff",
}


def is_write(server: str, tool: str) -> bool:
    if server == "slack":
        return tool in SLACK_WRITES
    if server == "linear":
        return tool in LINEAR_WRITES or tool.startswith(LINEAR_WRITE_PREFIXES)
    raise ValueError(f"Unknown server: {server}")


def synthetic_success(server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Return an unmistakable non-production result with a stable fake identifier."""
    return {
        "ok": True,
        "synthetic": True,
        "server": server,
        "tool": tool,
        "message": "Evaluation write intercepted; no external state changed.",
        "received_arguments": arguments,
        "id": f"eval-{server}-{tool}",
    }
