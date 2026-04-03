"""
Slack MCP Server — Enterprise Ready
======================================
Plug-and-play FastMCP server for Slack.

Client credentials (set in .env or MCP server config env block):
    SLACK_BOT_TOKEN  Slack Bot User OAuth Token (starts with xoxb-)
                     Obtain at: https://api.slack.com/apps > OAuth & Permissions

Required OAuth Scopes:
    channels:read, channels:history, groups:read, groups:history,
    chat:write, users:read, users:read.email,
    reactions:write, files:write, files:read

MCP config example (Claude Desktop / agent framework):
    {
      "mcpServers": {
        "slack": {
          "command": "python",
          "args": ["server.py"],
          "cwd": "/path/to/Slack",
          "env": { "SLACK_BOT_TOKEN": "xoxb-your-token-here" }
        }
      }
    }
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from agentops.sdk.decorators import tool as agentops_tool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [slack-mcp]  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "").strip()
if not SLACK_BOT_TOKEN:
    logger.error("SLACK_BOT_TOKEN is not set. Configure it in .env or MCP server env block.")
    sys.exit(1)
logger.info("Slack MCP Server starting — token configured OK")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "slack",
    instructions=(
        "Slack connector. Full access to channels, messages, users, and files. "
        "Credentials are pre-configured — just call tools directly."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> WebClient:
    return WebClient(token=SLACK_BOT_TOKEN)


def _ok(resp: Any) -> None:
    if not resp.get("ok"):
        raise RuntimeError(f"Slack API error: {resp.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------

@agentops_tool(name="slack_ping")
@mcp.tool()
def ping() -> str:
    """Verify the bot token is valid and return workspace info."""
    try:
        resp = _client().auth_test()
        _ok(resp)
        logger.info("ping: team=%s bot=%s", resp["team"], resp["bot_id"])
        return (
            f"Slack connection successful. "
            f"Workspace: {resp['team']}  |  Bot: {resp['user']}  |  URL: {resp['url']}"
        )
    except (SlackApiError, RuntimeError) as e:
        logger.warning("ping: failed — %s", e)
        return f"Slack connection failed: {e}"


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

@agentops_tool(name="slack_list_channels")
@mcp.tool()
def list_channels(
    limit: int = 200,
    exclude_archived: bool = True,
    types: str = "public_channel,private_channel",
) -> List[Dict[str, Any]]:
    """
    List all channels the bot has access to.

    Args:
        limit: Max channels to return (default 200).
        exclude_archived: Skip archived channels (default True).
        types: Comma-separated types: public_channel, private_channel, mpim, im.
    """
    try:
        resp = _client().conversations_list(limit=limit, exclude_archived=exclude_archived, types=types)
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


# @mcp.tool()  # not needed — channel messaging only
# def get_channel_info(channel_id: str) -> Dict[str, Any]: ...


# @mcp.tool()  # not needed — channel messaging only
# def get_channel_history(channel_id, limit, oldest, latest): ...


# @mcp.tool()  # not needed — channel messaging only
# def get_thread_replies(channel_id, thread_ts, limit): ...


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

@agentops_tool(name="slack_send_message")
@mcp.tool()
def send_message(
    channel_id: str,
    text: str,
    thread_ts: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Send a message to a channel or as a thread reply.

    Args:
        channel_id: Target channel ID.
        text: Plain text message.
        thread_ts: Parent message ts to reply in a thread.
        blocks: Optional Block Kit payload for rich formatting.

    Returns:
        {"ts": "<timestamp>", "channel": "<channel_id>"}
    """
    try:
        kwargs: Dict[str, Any] = {"channel": channel_id, "text": text}
        if thread_ts: kwargs["thread_ts"] = thread_ts
        if blocks: kwargs["blocks"] = blocks
        resp = _client().chat_postMessage(**kwargs)
        _ok(resp)
        logger.info("send_message: sent to %s ts=%s", channel_id, resp["ts"])
        return {"ts": resp["ts"], "channel": resp["channel"]}
    except (SlackApiError, RuntimeError) as e:
        raise RuntimeError(f"Failed to send message: {e}")


# @mcp.tool()  # not needed — channel messaging only
# def update_message(channel_id, ts, text): ...


# @mcp.tool()  # not needed — channel messaging only
# def delete_message(channel_id, ts): ...


# @mcp.tool()  # not needed — channel messaging only
# def add_reaction(channel_id, ts, emoji): ...


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

# @mcp.tool()  # not needed — channel messaging only
# def list_users(limit): ...


# @mcp.tool()  # not needed — channel messaging only
# def get_user_info(user_id): ...


# @mcp.tool()  # not needed — channel messaging only
# def lookup_user_by_email(email): ...


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

# @mcp.tool()  # not needed — channel messaging only
# def upload_file(channel_id, filename, content, title, initial_comment): ...


# @mcp.tool()  # not needed — channel messaging only
# def list_files(channel_id, count): ...


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8010"))
    logger.info("Starting Slack MCP server on port %d", port)
    mcp.run(transport="http", port=port)
