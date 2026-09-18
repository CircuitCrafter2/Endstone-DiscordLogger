"""Configuration manager for DiscordLogger plugin.

Handles loading, validation, and access to plugin configuration.
"""

from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING, Any, Literal

import tomli
import tomli_w

if TYPE_CHECKING:
    from .plugin import DiscordLoggerPlugin


# Type alias for module names
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

# Default configuration
DEFAULT_CONFIG: dict[str, Any] = {
    # Webhook URLs for each module
    "webhooks": {
        "player_join": "",
        "player_quit": "",
        "server_start": "",
        "server_stop": "",
        "server_crash": "",
        "player_command": "",
        "console_command": "",
        "chat_message": ""
    },
    # Global webhook URL (used if module-specific URL is empty)
    "global_webhook": "",
    # Custom webhooks that can be used via API
    "custom_webhooks": {},
    # Enabled modules
    "enabled": {
        "player_join": True,
        "player_quit": True,
        "server_start": True,
        "server_stop": True,
        "server_crash": True,
        "player_command": True,
        "console_command": True,
        "chat_message": True
    },
    # Language settings
    "language": "en",
    # Message formatting
    "formatting": {
        "include_timestamp": True,
        "include_server_name": True,
        "use_embeds": True,
        "embed_color": "0x3498DB"
    },
    # Filter settings
    "filters": {
        "ignored_commands": ["list", "help", "tellraw", "title"],
        "ignored_chat_patterns": []
    },
    # Bot settings
    "bot": {
        "username": "Server Logger",
        "avatar_url": ""
    }
}


class ConfigManager:
    """Manages plugin configuration with validation."""

    # Valid modules
    VALID_MODULES: tuple[ModuleName, ...] = (
        "player_join",
        "player_quit",
        "server_start",
        "server_stop",
        "server_crash",
        "player_command",
        "console_command",
        "chat_message"
    )

    def __init__(self, plugin: "DiscordLoggerPlugin") -> None:
        self._plugin = plugin
        self._config: dict[str, Any] = {}
        self._file_path: str = ""

    def load(self, file_path: str) -> None:
        """Load configuration from file.

        Args:
            file_path: Path to the config file
        """
        self._file_path = file_path

        try:
            with open(file_path, "rb") as f:
                self._config = tomli.load(f)
            self._validate()
            self._migrate()
        except FileNotFoundError:
            # Create default config
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
        except (tomli.TOMLDecodeError, ValueError) as e:
            self._plugin.logger.error(f"Error loading config: {e}")
            self._backup_invalid_config()
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

    def save(self) -> None:
        """Save current configuration to file."""
        if not self._file_path:
            return

        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "wb") as f:
                tomli_w.dump(self._config, f)
        except (IOError, OSError) as e:
            self._plugin.logger.error(f"Error saving config: {e}")

    def _backup_invalid_config(self) -> None:
        """Keep a copy of an invalid config before writing defaults."""
        if not self._file_path or not os.path.exists(self._file_path):
            return

        backup_path = f"{self._file_path}.broken"
        try:
            os.replace(self._file_path, backup_path)
            self._plugin.logger.warning(
                f"Invalid config moved to {backup_path}; writing defaults."
            )
        except OSError as e:
            self._plugin.logger.error(f"Error backing up invalid config: {e}")

    def _validate(self) -> None:
        """Validate configuration values."""
        # Ensure all webhook entries exist
        for module in self.VALID_MODULES:
            if "webhooks" not in self._config:
                self._config["webhooks"] = {}
            if module not in self._config["webhooks"]:
                self._config["webhooks"][module] = ""

        # Ensure all enabled entries exist
        if "enabled" not in self._config:
            self._config["enabled"] = {}
        for module in self.VALID_MODULES:
            if module not in self._config["enabled"]:
                self._config["enabled"][module] = True

        # Validate types
        if not isinstance(self._config.get("enabled"), dict):
            self._config["enabled"] = {}
        if not isinstance(self._config.get("webhooks"), dict):
            self._config["webhooks"] = {}

        # Ensure language is valid
        if "language" not in self._config:
            self._config["language"] = "en"

    def _migrate(self) -> None:
        """Migrate configuration from older versions."""
        # Add any new modules that might be missing
        for module in self.VALID_MODULES:
            if "webhooks" not in self._config:
                self._config["webhooks"] = {}
            if module not in self._config["webhooks"]:
                self._config["webhooks"][module] = ""

            if "enabled" not in self._config:
                self._config["enabled"] = {}
            if module not in self._config["enabled"]:
                self._config["enabled"][module] = True

    def get_webhook_url(self, module: ModuleName) -> str:
        """Get webhook URL for a specific module.

        Falls back to global webhook if module-specific URL is empty.

        Args:
            module: The module name

        Returns:
            The webhook URL
        """
        module_url = self._config.get("webhooks", {}).get(module, "")
        if module_url and module_url.strip():
            return module_url
        return self._config.get("global_webhook", "")

    def is_enabled(self, module: ModuleName) -> bool:
        """Check if a module is enabled.

        Args:
            module: The module name

        Returns:
            True if enabled, False otherwise
        """
        return self._config.get("enabled", {}).get(module, True)

    def get_language(self) -> str:
        """Get the configured language.

        Returns:
            Language code (e.g., 'en', 'fr')
        """
        return self._config.get("language", "en")

    def get_bot_username(self) -> str:
        """Get the configured bot username.

        Returns:
            Bot username
        """
        username = self._config.get("bot", {}).get("username", "Server Logger")
        if not isinstance(username, str):
            return "Server Logger"
        if "discord" in username.lower():
            return "Server Logger"
        return username

    def get_bot_avatar(self) -> str:
        """Get the configured bot avatar URL.

        Returns:
            Bot avatar URL
        """
        return self._config.get("bot", {}).get("avatar_url", "")

    def get_embed_color(self) -> int:
        """Get the configured embed color.

        Returns:
            Embed color as hex integer
        """
        color_str = self._config.get("formatting", {}).get("embed_color", "0x3498DB")
        try:
            return int(color_str, 16)
        except ValueError:
            return 0x3498DB

    def use_embeds(self) -> bool:
        """Check if embeds should be used.

        Returns:
            True if embeds are enabled
        """
        return self._config.get("formatting", {}).get("use_embeds", True)

    def get_ignored_commands(self) -> list[str]:
        """Get list of ignored commands.

        Returns:
            List of command names to ignore
        """
        return self._config.get("filters", {}).get("ignored_commands", [])

    def get_ignored_chat_patterns(self) -> list[str]:
        """Get list of ignored chat patterns.

        Returns:
            List of regex patterns to ignore in chat
        """
        return self._config.get("filters", {}).get("ignored_chat_patterns", [])

    def get_config(self) -> dict[str, Any]:
        """Get the raw configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    def set_webhook_url(self, module: ModuleName, url: str) -> None:
        """Set webhook URL for a module.

        Args:
            module: The module name
            url: The webhook URL
        """
        if "webhooks" not in self._config:
            self._config["webhooks"] = {}
        self._config["webhooks"][module] = url

    def set_enabled(self, module: ModuleName, enabled: bool) -> None:
        """Enable or disable a module.

        Args:
            module: The module name
            enabled: Whether to enable the module
        """
        if "enabled" not in self._config:
            self._config["enabled"] = {}
        self._config["enabled"][module] = enabled

    def set_language(self, language: str) -> None:
        """Set the plugin language.

        Args:
            language: Language code
        """
        self._config["language"] = language

    def reload(self) -> None:
        """Reload configuration from file."""
        if self._file_path:
            self.load(self._file_path)

    # Custom webhook methods
    def get_custom_webhook_url(self, name: str) -> str:
        """Get URL for a custom webhook.

        Args:
            name: Custom webhook name

        Returns:
            The webhook URL or empty string if not found
        """
        custom_webhooks = self._config.get("custom_webhooks", {})
        return custom_webhooks.get(name, "")

    def set_custom_webhook_url(self, name: str, url: str) -> None:
        """Set URL for a custom webhook.

        Args:
            name: Custom webhook name
            url: Webhook URL
        """
        if "custom_webhooks" not in self._config:
            self._config["custom_webhooks"] = {}
        self._config["custom_webhooks"][name] = url

    def remove_custom_webhook(self, name: str) -> bool:
        """Remove a custom webhook.

        Args:
            name: Custom webhook name

        Returns:
            True if removed, False if not found
        """
        if "custom_webhooks" not in self._config:
            return False
        if name in self._config["custom_webhooks"]:
            del self._config["custom_webhooks"][name]
            return True
        return False

    def get_all_custom_webhooks(self) -> dict[str, str]:
        """Get all custom webhooks.

        Returns:
            Dictionary of custom webhook names to URLs
        """
        return self._config.get("custom_webhooks", {}).copy()
