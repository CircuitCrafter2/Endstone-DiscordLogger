# DiscordLogger

An Endstone plugin for logging server events to Discord webhooks.

## Features

- **Player Events**: Log player join and quit events
- **Server Events**: Log server start, stop, and crash events
- **Command Logging**: Log player and console commands
- **Chat Logging**: Log player chat messages
- **Multi-Webhook**: Configure different Discord webhook URLs for each event type
- **Configurable**: All features can be enabled/disabled via `config.toml`
- **International**: Support for multiple languages (English and French by default)
- **Public API**: Allow other plugins to send logs through DiscordLogger
- **Test Command**: Test webhook configuration with `/test <module>` command

## Installation

1. Download the `.whl` file from the releases page
2. Copy it to your server's `plugins/` folder
3. Restart the server

Or build from source:

```bash
uv build
# Copy the .whl from dist/ to your plugins folder
```

## Configuration

On first startup, the plugin will create a `config.toml` file in its data folder
(`plugins/discord_logger/`). Edit this file to configure the plugin.

### Example Configuration

```toml
# Global webhook URL - used when a module-specific URL is not set
global_webhook = "https://discord.com/api/webhooks/your-webhook-id/your-token"

# Webhook URLs for each module
[webhooks]
player_join = "https://discord.com/api/webhooks/join-webhook"
player_quit = "https://discord.com/api/webhooks/quit-webhook"
server_start = ""
server_stop = ""
server_crash = ""
player_command = ""
console_command = ""
chat_message = ""

# Enable/disable logging for each module
[enabled]
player_join = true
player_quit = true
server_start = true
server_stop = true
server_crash = true
player_command = true
console_command = true
chat_message = true

# Language settings
language = "en"

# Message formatting
[formatting]
use_embeds = true
embed_color = "0x3498DB"

# Filter settings
[filters]
ignored_commands = ["list", "help", "tellraw"]
ignored_chat_patterns = []

[bot]
username = "DiscordLogger"
avatar_url = ""
```

## Commands

- `/test <module>` - Test the webhook for a specific module (OP only)
  - Modules: `player_join`, `player_quit`, `server_start`, `server_stop`, `server_crash`, `player_command`, `console_command`, `chat_message`

## API Usage

Other plugins can use DiscordLogger's API to send their own logs:

```python
from endstone.plugin import Plugin

class MyPlugin(Plugin):
    def on_enable(self) -> None:
        # Get DiscordLogger API
        discord_logger = self.server.plugin_manager.get_plugin("discord_logger")
        if discord_logger:
            api = discord_logger.get_api()
            
            # Send a log through DiscordLogger to a specific URL
            await api.send_log(
                module="custom",
                message="My custom log message",
                webhook_url="https://discord.com/api/webhooks/your-webhook"
            )
            
            # Or register a custom webhook for reuse
            api.register_webhook(
                name="my_plugin_events",
                url="https://discord.com/api/webhooks/your-webhook"
            )
            
            # Then send to it later
            await api.send_to_webhook(
                webhook_name="my_plugin_events",
                message="Something happened in my plugin!",
                title="My Plugin Event",
                color=0xFF5733
            )
```

### API Methods

| Method | Description |
|--------|-------------|
| `send_log(module, message, webhook_url, ...)` | Send a log message with optional custom URL |
| `send_custom(webhook_url, message, ...)` | Send to a specific URL |
| `send_to_webhook(name, message, ...)` | Send to a registered custom webhook |
| `register_webhook(name, url)` | Register a custom webhook for later use |
| `unregister_webhook(name)` | Remove a registered custom webhook |
| `get_webhook_names()` | List all registered custom webhook names |
| `get_webhook_url(name)` | Get URL for a registered custom webhook |
| `is_enabled(module)` | Check if a module is enabled |
| `get_webhook_url(module)` | Get webhook URL for a standard module |
| `set_webhook_url(module, url)` | Set webhook URL for a standard module |
| `set_enabled(module, enabled)` | Enable/disable a standard module |

## Supported Events

| Event | Module | Description |
|-------|--------|-------------|
| PlayerJoinEvent | player_join | Player joins the server |
| PlayerQuitEvent | player_quit | Player leaves the server |
| ServerLoadEvent (STARTUP) | server_start | Server starts |
| PlayerCommandEvent | player_command | Player executes a command |
| ServerCommandEvent | console_command | Console executes a command |
| PlayerChatEvent | chat_message | Player sends a chat message |

**Notes**:
- Server stop and crash events are NOT automatically detected by the Endstone API. The `server_stop` and `server_crash` modules are available for use via the API only.
- To log server stop/crash, other plugins or manual calls to the API are required.

## Adding Translations

1. Create a new `.toml` file in `src/discord_logger/translations/` (e.g., `es.toml`)
2. Copy the structure from `en.toml` or `fr.toml`
3. Translate all the strings
4. Update the `language` setting in `config.toml` to use your new language

## Building

```bash
uv sync
uv build
```

The built `.whl` file will be in the `dist/` directory.

## License

MIT License
