"""Slack Web API client. User token from vault inject."""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

SLACK_BASE = "https://slack.com/api"


class SlackError(Exception):
    def __init__(self, message: str, error_code: str = "SLACK_ERROR", retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "error_message": str(self),
            "retryable": self.retryable,
            "original_provider_error": None,
        }


def _token_from_creds(credentials_json: Optional[str], credentials_path: Optional[str]) -> str:
    data: dict[str, Any] = {}
    if credentials_json:
        data = json.loads(credentials_json)
    elif credentials_path:
        with open(credentials_path, encoding="utf-8") as fh:
            data = json.load(fh)
    token = (data.get("access_token") or data.get("token") or "").strip()
    if not token:
        raise SlackError(
            "Credentials required: provide credentials_path or credentials_json",
            error_code="CREDENTIALS_REQUIRED",
        )
    return token


class SlackService:
    def __init__(
        self,
        credentials_json: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        self._token = _token_from_creds(credentials_json, credentials_path)

    def _call(self, method: str, **params) -> dict:
        resp = requests.post(
            f"{SLACK_BASE}/{method}",
            headers={"Authorization": f"Bearer {self._token}"},
            data={k: v for k, v in params.items() if v is not None},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise SlackError(
                f"Slack HTTP {resp.status_code}: {resp.text[:300]}",
                retryable=resp.status_code >= 500,
            )
        data = resp.json()
        if not data.get("ok"):
            raise SlackError(f"Slack API: {data.get('error') or 'unknown'}", error_code="SLACK_API_ERROR")
        return data

    def list_channels(self, limit: int = 100) -> list[dict]:
        data = self._call("conversations.list", limit=str(max(1, min(limit, 200))), types="public_channel,private_channel")
        return data.get("channels") or []

    def post_message(self, channel: str, text: str) -> dict:
        return self._call("chat.postMessage", channel=channel, text=text)

    def list_messages(self, channel: str, limit: int = 50) -> list[dict]:
        data = self._call("conversations.history", channel=channel, limit=str(max(1, min(limit, 200))))
        return data.get("messages") or []

    def search_messages(self, query: str, count: int = 20) -> list[dict]:
        data = self._call("search.messages", query=query, count=str(max(1, min(count, 100))))
        matches = ((data.get("messages") or {}).get("matches")) or []
        return matches
