"""
Slack tools for direct use in LangGraph agents.

No MCP server required — tools call the Slack API directly using the Slack SDK.
SLACK_BOT_TOKEN must be set in the environment or .env file.

Required Slack OAuth scopes:
    channels:read, chat:write
"""

import logging
import os
from typing import Any, Dict, List, Optional

from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> WebClient:
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not set. Add it to .env or the environment.")
    return WebClient(token=token)


def _ok(resp: Any) -> None:
    if not resp.get("ok"):
        raise RuntimeError(f"Slack API error: {resp.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def slack_send_message(
    channel_id: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to a Slack channel or as a thread reply.

    Args:
        channel_id: The Slack channel ID to send the message to (e.g. C01234567).
        text: The plain-text content of the message.
        thread_ts: Optional. Parent message timestamp — supply this to reply in a thread.

    Returns:
        A dict with 'ts' (message timestamp) and 'channel' (channel ID).
    """
    try:
        client = _get_client()
        kwargs: Dict[str, Any] = {"channel": channel_id, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        resp = client.chat_postMessage(**kwargs)
        _ok(resp)
        logger.info("slack_send_message: sent to %s ts=%s", channel_id, resp["ts"])
        return {"ts": resp["ts"], "channel": resp["channel"]}
    except (SlackApiError, RuntimeError) as e:
        raise RuntimeError(f"Failed to send message: {e}")


@tool
def slack_list_channels(
    limit: int = 200,
    exclude_archived: bool = True,
) -> List[Dict[str, Any]]:
    """List all Slack channels the bot has access to.

    Args:
        limit: Maximum number of channels to return (default 200).
        exclude_archived: Whether to skip archived channels (default True).

    Returns:
        A list of channel dicts, each containing id, name, is_private, is_archived,
        num_members, topic, and purpose.
    """
    try:
        client = _get_client()
        resp = client.conversations_list(
            limit=limit,
            exclude_archived=exclude_archived,
            types="public_channel,private_channel",
        )
        _ok(resp)
        return [
            {
                "id": c["id"],
                "name": c.get("name"),
                "is_private": c.get("is_private", False),
                "is_archived": c.get("is_archived", False),
                "num_members": c.get("num_members"),
                "topic": c.get("topic", {}).get("value", ""),
                "purpose": c.get("purpose", {}).get("value", ""),
            }
            for c in resp["channels"]
        ]
    except (SlackApiError, RuntimeError) as e:
        raise RuntimeError(f"Failed to list channels: {e}")


@tool
def slack_ping() -> str:
    """Verify the Slack bot token is valid and return workspace info.

    Returns:
        A string with the workspace name, bot username, and workspace URL.
    """
    try:
        client = _get_client()
        resp = client.auth_test()
        _ok(resp)
        logger.info("slack_ping: team=%s bot=%s", resp["team"], resp["bot_id"])
        return (
            f"Slack connection successful. "
            f"Workspace: {resp['team']}  |  Bot: {resp['user']}  |  URL: {resp['url']}"
        )
    except (SlackApiError, RuntimeError) as e:
        return f"Slack connection failed: {e}"
