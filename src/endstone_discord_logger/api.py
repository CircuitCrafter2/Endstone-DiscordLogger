"""Public API for DiscordLogger plugin.

Allows other plugins to send logs through DiscordLogger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .plugin import DiscordLoggerPlugin


ModuleName = Literal[
    "player_join",
    "player_quit",
    "server_start",
    "server_stop",
    "server_crash",
    "player_command",
    "console_command",
    "chat_message"
]

# Type for custom webhook names (can be any string)
CustomWebhookName = str


class DiscordLoggerAPI:
    """Public API for sending logs to Discord through DiscordLogger."""

    def __init__(self, plugin: "DiscordLoggerPlugin") -> None:
        self._plugin = plugin

    async def send_log(
        self,
        module: ModuleName,
        message: str,
        webhook_url: str | None = None,
        use_embed: bool = True,
        color: int | None = None,
        title: str | None = None,
        username: str | None = None,
        avatar_url: str | None = None
    ) -> bool:
        """Send a log message to Discord.

        Args:
            module: Module name (determines default webhook URL if not provided)
            message: The message to send
            webhook_url: Custom webhook URL (overrides module default)
            use_embed: Whether to use embed formatting
            color: Embed color (hex integer)
            title: Embed title
            username: Bot username override
            avatar_url: Bot avatar URL override

        Returns:
            True if successful, False otherwise
        """
        # Determine webhook URL
        if webhook_url is None:
            # Use module-specific or global webhook
            if module in (
                "player_join", "player_quit", "server_start",
                "server_stop", "server_crash", "player_command",
                "console_command", "chat_message"
            ):
                webhook_url = self._plugin._config.get_webhook_url(module)
            else:
                webhook_url = self._plugin._config.get_webhook_url("custom")

        if not webhook_url:
            self._plugin.logger.warning(f"No webhook URL for module {module}")
            return False

        # Determine color
        if color is None:
            color = self._plugin._config.get_embed_color()

        # Determine username
        if username is None:
            username = self._plugin._config.get_bot_username()

        # Determine avatar URL
        if avatar_url is None:
            avatar_url = self._plugin._config.get_bot_avatar()

        # Determine if embeds should be used
        if use_embed and not self._plugin._config.use_embeds():
            use_embed = False

        try:
            if use_embed:
                embed = self._plugin._webhook_sender.create_embed(
                    title=title or module,
                    description=message,
                    color=color,
                    footer=username
                )
                success = await self._plugin._webhook_sender.send_webhook(
                    webhook_url,
                    embeds=[embed],
                    username=username,
                    avatar_url=avatar_url
                )
            else:
                success = await self._plugin._webhook_sender.send_webhook(
                    webhook_url,
                    content=message,
                    username=username,
                    avatar_url=avatar_url
                )

            if not success:
                self._plugin.logger.warning(f"Failed to send API log for {module}")

            return success

        except Exception as e:
            self._plugin.logger.error(f"Error sending API log: {e}")
            return False

    async def send_custom(
        self,
        webhook_url: str,
        message: str,
        use_embed: bool = True,
        color: int | None = None,
        title: str | None = None,
        username: str | None = None,
        avatar_url: str | None = None
    ) -> bool:
        """Send a custom message to a specific webhook.

        Args:
            webhook_url: The webhook URL to send to
            message: The message to send
            use_embed: Whether to use embed formatting
            color: Embed color (hex integer)
            title: Embed title
            username: Bot username override
            avatar_url: Bot avatar URL override

        Returns:
            True if successful, False otherwise
        """
        return await self.send_log(
            "custom",
            message,
            webhook_url=webhook_url,
            use_embed=use_embed,
            color=color,
            title=title,
            username=username,
            avatar_url=avatar_url
        )

    def is_enabled(self, module: ModuleName) -> bool:
        """Check if a module is enabled.

        Args:
            module: Module name

        Returns:
            True if enabled, False otherwise
        """
        if module in (
            "player_join", "player_quit", "server_start",
            "server_stop", "server_crash", "player_command",
            "console_command", "chat_message"
        ):
            return self._plugin._config.is_enabled(module)
        return True

    def get_webhook_url(self, module: ModuleName) -> str:
        """Get the webhook URL for a module.

        Args:
            module: Module name

        Returns:
            Webhook URL or empty string
        """
        if module in (
            "player_join", "player_quit", "server_start",
            "server_stop", "server_crash", "player_command",
            "console_command", "chat_message"
        ):
            return self._plugin._config.get_webhook_url(module)
        return ""

    def set_webhook_url(self, module: ModuleName, url: str) -> None:
        """Set the webhook URL for a module.

        Args:
            module: Module name
            url: Webhook URL
        """
        if module in (
            "player_join", "player_quit", "server_start",
            "server_stop", "server_crash", "player_command",
            "console_command", "chat_message"
        ):
            self._plugin._config.set_webhook_url(module, url)
            self._plugin._config.save()

    def set_enabled(self, module: ModuleName, enabled: bool) -> None:
        """Enable or disable a module.

        Args:
            module: Module name
            enabled: Whether to enable
        """
        if module in (
            "player_join", "player_quit", "server_start",
            "server_stop", "server_crash", "player_command",
            "console_command", "chat_message"
        ):
            self._plugin._config.set_enabled(module, enabled)
            self._plugin._config.save()

    # Custom webhook management methods
    def register_webhook(self, name: CustomWebhookName, url: str) -> None:
        """Register a custom webhook that can be used via the API.

        This allows other plugins to define their own webhook endpoints
        with custom names for logging specific events.

        Args:
            name: Unique name for the custom webhook
            url: Discord webhook URL
        """
        self._plugin._config.set_custom_webhook_url(name, url)
        self._plugin._config.save()

    def unregister_webhook(self, name: CustomWebhookName) -> bool:
        """Unregister a custom webhook.

        Args:
            name: Name of the custom webhook to remove

        Returns:
            True if the webhook was found and removed, False otherwise
        """
        removed = self._plugin._config.remove_custom_webhook(name)
        if removed:
            self._plugin._config.save()
        return removed

    def get_webhook_names(self) -> list[CustomWebhookName]:
        """Get list of all registered custom webhook names.

        Returns:
            List of custom webhook names
        """
        return list(self._plugin._config.get_all_custom_webhooks().keys())

    def get_webhook_url(self, name: CustomWebhookName) -> str:
        """Get the URL for a registered custom webhook.

        Args:
            name: Name of the custom webhook

        Returns:
            Webhook URL or empty string if not found
        """
        return self._plugin._config.get_custom_webhook_url(name)

    async def send_to_webhook(
        self,
        webhook_name: CustomWebhookName,
        message: str,
        use_embed: bool = True,
        color: int | None = None,
        title: str | None = None,
        username: str | None = None,
        avatar_url: str | None = None
    ) -> bool:
        """Send a message to a registered custom webhook.

        Args:
            webhook_name: Name of the registered custom webhook
            message: The message to send
            use_embed: Whether to use embed formatting
            color: Embed color (hex integer)
            title: Embed title
            username: Bot username override
            avatar_url: Bot avatar URL override

        Returns:
            True if successful, False otherwise
        """
        url = self._plugin._config.get_custom_webhook_url(webhook_name)
        if not url:
            self._plugin.logger.warning(f"Custom webhook '{webhook_name}' not found")
            return False

        return await self.send_log(
            module="custom",
            message=message,
            webhook_url=url,
            use_embed=use_embed,
            color=color,
            title=title,
            username=username,
            avatar_url=avatar_url
        )
