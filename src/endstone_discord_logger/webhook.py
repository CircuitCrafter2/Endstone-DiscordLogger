"""Discord webhook sender module.

Handles sending messages to Discord webhooks with proper formatting.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import aiohttp

if TYPE_CHECKING:
    from .plugin import DiscordLoggerPlugin


class WebhookSender:
    """Handles sending messages to Discord webhooks."""

    def __init__(self, plugin: "DiscordLoggerPlugin") -> None:
        self._plugin = plugin
        self._user_agent = f"DiscordLogger/{plugin.api_version}"

    async def initialize(self) -> None:
        """Initialize the webhook sender."""
        return None

    async def close(self) -> None:
        """Close the webhook sender."""
        return None

    async def send_webhook(
        self,
        url: str,
        content: str | None = None,
        embeds: list[dict[str, Any]] | None = None,
        username: str | None = None,
        avatar_url: str | None = None
    ) -> bool:
        """Send a message to a Discord webhook.

        Args:
            url: The webhook URL
            content: The plain text content
            embeds: List of embed objects
            username: Override the webhook username
            avatar_url: Override the webhook avatar

        Returns:
            True if successful, False otherwise
        """
        if not url or not url.strip():
            return False

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds
        safe_username = self._sanitize_username(username)
        if safe_username:
            payload["username"] = safe_username
        if avatar_url:
            payload["avatar_url"] = avatar_url

        if "content" not in payload and "embeds" not in payload:
            self._plugin.logger.error("Webhook payload is empty")
            return False

        try:
            async with aiohttp.ClientSession(
                headers={"User-Agent": self._user_agent},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 204:
                        return True
                    elif response.status == 404:
                        self._plugin.logger.error(
                            f"Invalid webhook URL: {self._redact_webhook_url(url)}"
                        )
                    elif response.status == 400:
                        text = await response.text()
                        self._plugin.logger.error(
                            "Bad request to webhook "
                            f"{self._redact_webhook_url(url)}: {text}"
                        )
                    elif response.status >= 500:
                        self._plugin.logger.error(
                            f"Discord server error for webhook {self._redact_webhook_url(url)}"
                        )
                    else:
                        text = await response.text()
                        self._plugin.logger.error(
                            f"Failed to send webhook ({response.status}): {text}"
                        )
                    return False
        except aiohttp.ClientError as e:
            self._plugin.logger.error(f"Webhook error: {e}")
            return False
        except asyncio.TimeoutError:
            self._plugin.logger.error("Webhook request timed out")
            return False

    def _redact_webhook_url(self, url: str) -> str:
        """Hide the webhook token before logging a URL."""
        try:
            parts = urlsplit(url)
            path_parts = parts.path.strip("/").split("/")
            if len(path_parts) >= 4 and path_parts[-2].isdigit():
                path_parts[-1] = "<redacted>"
                path = "/" + "/".join(path_parts)
                return parts._replace(path=path, query="", fragment="").geturl()
        except ValueError:
            pass
        return "<redacted webhook>"

    def _sanitize_username(self, username: str | None) -> str | None:
        """Return a Discord-accepted webhook username."""
        if not username or not username.strip():
            return None
        if "discord" in username.lower():
            return "Server Logger"
        return username

    def create_embed(
        self,
        title: str | None = None,
        description: str | None = None,
        color: int = 0x3498DB,
        fields: list[dict[str, Any]] | None = None,
        footer: str | None = None,
        timestamp: bool = True
    ) -> dict[str, Any]:
        """Create a Discord embed object.

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex integer)
            fields: List of field objects
            footer: Embed footer text
            timestamp: Include current timestamp

        Returns:
            Dictionary representing the embed
        """
        embed: dict[str, Any] = {"color": color}

        if title:
            embed["title"] = title
        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if timestamp:
            embed["timestamp"] = datetime.now(timezone.utc).isoformat()

        return embed

    def create_field(name: str, value: str, inline: bool = False) -> dict[str, Any]:
        """Create an embed field object.

        Args:
            name: Field name
            value: Field value
            inline: Whether field should be inline

        Returns:
            Dictionary representing the field
        """
        return {"name": name, "value": value, "inline": inline}
