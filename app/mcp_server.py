"""Slack MCP Server — list channels, post, list/search messages."""

from __future__ import annotations

import logging
from typing import Optional

from fastmcp import FastMCP
from pydantic import Field
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.services.slack_service import SlackError, SlackService
from app.capability_bind import bind_declared_capabilities

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="slack",
    instructions="Slack user-token tools. Credentials from Studio Connect. Posting requires confirm=true.",
)

_CREDS_JSON = Field(default=None, description="OAuth token JSON from Studio vault inject")
_CREDS_PATH = Field(default=None, description="Local credentials JSON path")


def _creds_required() -> dict:
    return {
        "error_code": "CREDENTIALS_REQUIRED",
        "error_message": "Provide credentials_path or credentials_json",
        "retryable": False,
        "original_provider_error": None,
    }


def _confirm_required() -> dict:
    return {
        "error_code": "CONFIRM_REQUIRED",
        "error_message": "Set confirm=true to execute this side-effecting tool",
        "retryable": False,
        "original_provider_error": None,
    }


def _svc(credentials_path, credentials_json) -> SlackService:
    return SlackService(credentials_json=credentials_json, credentials_path=credentials_path)


@mcp.tool()
def slack_list_channels(
    credentials_path: Optional[str] = _CREDS_PATH,
    credentials_json: Optional[str] = _CREDS_JSON,
    limit: int = Field(default=100),
) -> dict:
    """List Slack channels visible to the connected user.

        Capabilities: slack.slack_list_channels
Outputs: success
        """
    try:
        if not credentials_path and not credentials_json:
            return {"success": False, "error": _creds_required()}
        channels = _svc(credentials_path, credentials_json).list_channels(limit)
        return {"success": True, "channels": channels, "total_count": len(channels)}
    except SlackError as e:
        return {"success": False, "error": e.to_dict()}


@mcp.tool()
def slack_post_message(
    channel: str = Field(..., description="Channel id or name"),
    text: str = Field(..., description="Message text", json_schema_extra={"x-datumbridge-encoding": "plain"}),
    credentials_path: Optional[str] = _CREDS_PATH,
    credentials_json: Optional[str] = _CREDS_JSON,
    confirm: bool = Field(default=False),
    dry_run: bool = Field(default=False),
) -> dict:
    """Post a message to a Slack channel. Requires confirm=true.

        Capabilities: slack.slack_post_message
Outputs: success
        """
    try:
        if not credentials_path and not credentials_json:
            return {"success": False, "error": _creds_required()}
        if dry_run:
            return {"success": True, "dry_run": True, "message": "Would post message", "channel": channel}
        if not confirm:
            return {"success": False, "error": _confirm_required()}
        result = _svc(credentials_path, credentials_json).post_message(channel, text)
        return {"success": True, "message": "Posted", "result": result}
    except SlackError as e:
        return {"success": False, "error": e.to_dict()}


@mcp.tool()
def slack_list_messages(
    channel: str = Field(..., description="Channel id"),
    credentials_path: Optional[str] = _CREDS_PATH,
    credentials_json: Optional[str] = _CREDS_JSON,
    limit: int = Field(default=50),
) -> dict:
    """List recent messages in a Slack channel.

        Capabilities: slack.slack_list_messages
Outputs: success
        """
    try:
        if not credentials_path and not credentials_json:
            return {"success": False, "error": _creds_required()}
        messages = _svc(credentials_path, credentials_json).list_messages(channel, limit)
        return {"success": True, "messages": messages, "total_count": len(messages)}
    except SlackError as e:
        return {"success": False, "error": e.to_dict()}


@mcp.tool()
def slack_search_messages(
    query: str = Field(..., description="Slack search query"),
    credentials_path: Optional[str] = _CREDS_PATH,
    credentials_json: Optional[str] = _CREDS_JSON,
    count: int = Field(default=20),
) -> dict:
    """Search Slack messages the user can access.

        Capabilities: slack.slack_search_messages
Outputs: success
        """
    try:
        if not credentials_path and not credentials_json:
            return {"success": False, "error": _creds_required()}
        matches = _svc(credentials_path, credentials_json).search_messages(query, count)
        return {"success": True, "matches": matches, "total_count": len(matches)}
    except SlackError as e:
        return {"success": False, "error": e.to_dict()}



bind_declared_capabilities(mcp)

_base_app = mcp.http_app()


async def health(_request):
    return JSONResponse({"status": "ok", "service": "slack-mcp"})


http_app = Starlette(
    routes=[Route("/health", health), Mount("/", _base_app)],
    lifespan=getattr(_base_app, "lifespan", None),
)

if __name__ == "__main__":
    mcp.run()
