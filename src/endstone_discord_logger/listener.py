"""Event listener for DiscordLogger plugin.

Handles all server events and sends them to Discord webhooks.
"""

import re
from typing import TYPE_CHECKING, Literal

from endstone.event import (
    EventPriority,
    PlayerChatEvent,
    PlayerCommandEvent,
    PlayerJoinEvent,
    PlayerQuitEvent,
    ServerCommandEvent,
    ServerLoadEvent,
    event_handler
)

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


class DiscordLoggerListener:
    """Listens to server events and sends them to Discord."""

    def __init__(self, plugin: "DiscordLoggerPlugin") -> None:
        self._plugin = plugin

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        """Handle player join event."""
        if not self._plugin._config.is_enabled("player_join"):
            return

        webhook_url = self._plugin._config.get_webhook_url("player_join")
        if not webhook_url:
            return

        player_name = event.player.name
        message = self._plugin._translations.translate(
            "events.player_join", player=player_name
        )

        self._plugin._run_async(self._send_webhook(
            "player_join",
            webhook_url,
            message,
            color=0x2ECC71,
            title="Player Joined"
        ))

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        """Handle player quit event."""
        if not self._plugin._config.is_enabled("player_quit"):
            return

        webhook_url = self._plugin._config.get_webhook_url("player_quit")
        if not webhook_url:
            return

        player_name = event.player.name
        message = self._plugin._translations.translate(
            "events.player_quit", player=player_name
        )

        self._plugin._run_async(self._send_webhook(
            "player_quit",
            webhook_url,
            message,
            color=0xE74C3C,
            title="Player Left"
        ))

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_command(self, event: PlayerCommandEvent) -> None:
        """Handle player command event."""
        if not self._plugin._config.is_enabled("player_command"):
            return

        command_name = event.command.split()[0] if event.command else ""
        if command_name in self._plugin._config.get_ignored_commands():
            return

        webhook_url = self._plugin._config.get_webhook_url("player_command")
        if not webhook_url:
            return

        player_name = event.player.name
        command = event.command
        message = self._plugin._translations.translate(
            "commands.player_command",
            player=player_name,
            command=command
        )

        self._plugin._run_async(self._send_webhook(
            "player_command",
            webhook_url,
            message,
            color=0x3498DB,
            title="Player Command"
        ))

    @event_handler(priority=EventPriority.NORMAL)
    def on_server_command(self, event: ServerCommandEvent) -> None:
        """Handle server/console command event."""
        if not self._plugin._config.is_enabled("console_command"):
            return

        command_name = event.command.split()[0] if event.command else ""
        if command_name in self._plugin._config.get_ignored_commands():
            return

        webhook_url = self._plugin._config.get_webhook_url("console_command")
        if not webhook_url:
            return

        command = event.command
        message = self._plugin._translations.translate(
            "commands.console_command",
            command=command
        )

        self._plugin._run_async(self._send_webhook(
            "console_command",
            webhook_url,
            message,
            color=0x9B59B6,
            title="Console Command"
        ))

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_chat(self, event: PlayerChatEvent) -> None:
        """Handle player chat message event."""
        if not self._plugin._config.is_enabled("chat_message"):
            return

        webhook_url = self._plugin._config.get_webhook_url("chat_message")
        if not webhook_url:
            return

        player_name = event.player.name
        message = event.message

        for pattern in self._plugin._config.get_ignored_chat_patterns():
            if re.search(pattern, message):
                return

        chat_message = self._plugin._translations.translate(
            "commands.chat_message",
            player=player_name,
            message=message
        )

        self._plugin._run_async(self._send_webhook(
            "chat_message",
            webhook_url,
            chat_message,
            color=0x1ABC9C,
            title="Chat Message"
        ))

    @event_handler(priority=EventPriority.NORMAL)
    def on_server_load(self, event: ServerLoadEvent) -> None:
        """Handle server start/reload event."""
        # Only handle STARTUP, not RELOAD
        if event.type.name != "STARTUP":
            return
        if not self._plugin._config.is_enabled("server_start"):
            return

        webhook_url = self._plugin._config.get_webhook_url("server_start")
        if not webhook_url:
            return

        message = self._plugin._translations.translate("events.server_start")

        self._plugin._run_async(self._send_webhook(
            "server_start",
            webhook_url,
            message,
            color=0x2ECC71,
            title="Server Started"
        ))

    async def _send_webhook(
        self,
        module: ModuleName,
        url: str,
        message: str,
        color: int,
        title: str
    ) -> None:
        """Send a webhook message.

        Args:
            module: Module name for logging
            url: Webhook URL
            message: Message to send
            color: Embed color
            title: Embed title
        """
        try:
            use_embeds = self._plugin._config.use_embeds()

            if use_embeds:
                embed = self._plugin._webhook_sender.create_embed(
                    title=title,
                    description=message,
                    color=color,
                    footer=self._plugin._config.get_bot_username()
                )
                success = await self._plugin._webhook_sender.send_webhook(
                    url,
                    embeds=[embed],
                    username=self._plugin._config.get_bot_username(),
                    avatar_url=self._plugin._config.get_bot_avatar()
                )
            else:
                success = await self._plugin._webhook_sender.send_webhook(
                    url,
                    content=message,
                    username=self._plugin._config.get_bot_username(),
                    avatar_url=self._plugin._config.get_bot_avatar()
                )

            if not success:
                self._plugin.logger.warning(
                    f"Failed to send webhook for {module}"
                )

        except Exception as e:
            self._plugin.logger.error(f"Error sending webhook: {e}")
