"""DiscordLogger - An Endstone plugin for logging server events to Discord webhooks."""

from __future__ import annotations

import os
import shutil
from importlib import resources

import endstone.asyncio
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

try:
    from typing_extensions import override
except ImportError:
    from typing import override

from .api import DiscordLoggerAPI
from .config import ConfigManager
from .listener import DiscordLoggerListener
from .translations import TranslationManager
from .webhook import WebhookSender

MODULE_CHOICES = (
    "player_join",
    "player_quit",
    "server_start",
    "server_stop",
    "server_crash",
    "player_command",
    "console_command",
    "chat_message",
)


class DiscordLoggerPlugin(Plugin):
    """Main plugin class for DiscordLogger.

    Logs server events to Discord webhooks.
    """

    # Plugin metadata
    prefix = "DiscordLogger"
    api_version = "0.11"

    # Commands
    commands = {
        "test": {
            "description": "Test Discord webhook for a specific module",
            "usages": [f"/test <{'|'.join(MODULE_CHOICES)}>"],
            "permissions": ["discordlogger.command.test"],
        }
    }

    # Permissions
    permissions = {
        "discordlogger.command.test": {
            "description": "Allow testing Discord webhooks",
            "default": "op",
        }
    }

    def __init__(self) -> None:
        """Initialize the plugin."""
        super().__init__()

        # Initialize components (will be properly initialized in on_enable)
        self._config: ConfigManager | None = None
        self._translations: TranslationManager | None = None
        self._webhook_sender: WebhookSender | None = None
        self._api: DiscordLoggerAPI | None = None
        self._listener: DiscordLoggerListener | None = None

    @override
    def on_enable(self) -> None:
        """Initialization when plugin is enabled."""
        os.makedirs(self.data_folder, exist_ok=True)

        config_path = os.path.join(self.data_folder, "config.toml")
        if not os.path.exists(config_path):
            self._save_default_config(config_path)

        self._config = ConfigManager(self)
        self._config.load(config_path)

        self._translations = TranslationManager(self)
        language = self._config.get_language()
        self._translations.load_language(language)

        self._webhook_sender = WebhookSender(self)
        self._api = DiscordLoggerAPI(self)

        # Register event listener
        self._listener = DiscordLoggerListener(self)
        self.register_events(self._listener)

        # Log startup message
        self.logger.info("DiscordLogger enabled!")

    def _save_default_config(self, config_path: str) -> None:
        """Copy bundled default config to the plugin data folder."""
        if os.path.exists(config_path):
            return

        try:
            source = resources.files(__package__).joinpath("config.toml")
            with resources.as_file(source) as source_path:
                shutil.copyfile(source_path, config_path)
        except (FileNotFoundError, OSError) as e:
            self.logger.error(f"Error saving default config: {e}")

    @override
    def on_disable(self) -> None:
        """Cleanup when plugin is disabled."""
        # Log shutdown message
        self.logger.info("DiscordLogger disabled!")

        if self._webhook_sender is not None:
            self._run_async(self._close_webhook_sender())

        # Set listener to None to allow garbage collection
        self._listener = None

    async def _close_webhook_sender(self) -> None:
        """Async cleanup for webhook sender."""
        try:
            await self._webhook_sender.close()
        except Exception as e:
            self.logger.error(f"Error closing webhook sender: {e}")

    def _run_async(self, coroutine) -> None:
        """Run a coroutine on Endstone's async executor."""
        endstone.asyncio.submit(coroutine)

    def _run_sync(self, task) -> None:
        """Run a callback on the server thread."""
        self.server.scheduler.run_task(self, task)

    @override
    def on_command(
        self, sender: CommandSender, command: Command, args: list[str]
    ) -> bool:
        """Handle plugin commands."""
        if command.name == "test":
            return self._handle_test_command(sender, args)

        return False

    def _handle_test_command(
        self, sender: CommandSender, args: list[str]
    ) -> bool:
        """Handle the /test command."""
        if not args:
            sender.send_error_message(
                self._translations.translate("test.usage")
            )
            return False

        module = args[0].lower()

        if module not in MODULE_CHOICES:
            sender.send_error_message(
                self._translations.translate("test.invalid_module", module=module)
            )
            return False

        # Get webhook URL
        webhook_url = self._config.get_webhook_url(module)

        if not webhook_url:
            sender.send_error_message(
                self._translations.translate("errors.no_webhook_url", module=module)
            )
            return False

        # Create test message based on module
        test_message = self._get_test_message(module)
        sender.send_message(f"Sending DiscordLogger test for {module}...")

        # Send async webhook test
        self._run_async(self._send_test_webhook_and_report(
            module, webhook_url, test_message, sender
        ))

        return True

    async def _send_test_webhook_and_report(
        self,
        module: str,
        webhook_url: str,
        message: str,
        sender: CommandSender
    ) -> None:
        """Send a test webhook and report the result on the server thread."""
        success = await self._send_test_webhook(module, webhook_url, message)

        def report_result() -> None:
            if success:
                sender.send_message(
                    self._translations.translate("test.success", module=module)
                )
            else:
                sender.send_error_message(
                    self._translations.translate("test.failed", module=module)
                )

        self._run_sync(report_result)

    def _get_test_message(self, module: str) -> str:
        """Get a test message for the specified module.

        Args:
            module: Module name

        Returns:
            Test message
        """
        messages = {
            "player_join": "TestPlayer joined the server",
            "player_quit": "TestPlayer left the server",
            "server_start": "Server started (test)",
            "server_stop": "Server stopped (test)",
            "server_crash": "Server crashed! (test)",
            "player_command": "TestPlayer executed command: /test test",
            "console_command": "Console executed command: /test test",
            "chat_message": "TestPlayer: This is a test message"
        }
        return messages.get(module, f"Test message for {module}")

    async def _send_test_webhook(
        self,
        module: str,
        webhook_url: str,
        message: str
    ) -> bool:
        """Send a test webhook message.

        Args:
            module: Module name
            webhook_url: Webhook URL
            message: Test message
        Returns:
            True if the webhook was sent successfully.
        """
        color = 0x3498DB  # Default blue
        title = module.replace("_", " ").title()

        if self._config.use_embeds():
            embed = self._webhook_sender.create_embed(
                title=f"[TEST] {title}",
                description=f"*This is a test message*\n{message}",
                color=color,
                footer="DiscordLogger Test"
            )
            success = await self._webhook_sender.send_webhook(
                webhook_url,
                embeds=[embed],
                username=self._config.get_bot_username(),
                avatar_url=self._config.get_bot_avatar()
            )
        else:
            success = await self._webhook_sender.send_webhook(
                webhook_url,
                content=f"[TEST] {title}: {message}",
                username=self._config.get_bot_username(),
                avatar_url=self._config.get_bot_avatar()
            )

        return success

    def get_api(self) -> DiscordLoggerAPI:
        """Get the public API instance.

        Returns:
            DiscordLoggerAPI instance
        """
        return self._api
