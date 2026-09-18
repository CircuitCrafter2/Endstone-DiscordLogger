"""Translation manager for DiscordLogger plugin.

Handles loading and accessing translations for different languages.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import tomli

if TYPE_CHECKING:
    from .plugin import DiscordLoggerPlugin


class TranslationManager:
    """Manages plugin translations."""

    def __init__(self, plugin: "DiscordLoggerPlugin") -> None:
        self._plugin = plugin
        self._translations: dict[str, dict[str, str]] = {}
        self._current_language: str = "en"
        self._translations_dir: str = os.path.join(
            os.path.dirname(__file__), "translations"
        )

    def load_language(self, language: str) -> bool:
        """Load translations for a specific language.

        Args:
            language: Language code

        Returns:
            True if loaded successfully, False otherwise
        """
        self._current_language = language

        # Try to load the language file
        lang_file = os.path.join(self._translations_dir, f"{language}.toml")

        if not os.path.exists(lang_file):
            # Try with fallback (e.g., 'en_US' -> 'en')
            base_lang = language.split("_")[0]
            if base_lang != language:
                fallback_file = os.path.join(self._translations_dir, f"{base_lang}.toml")
                if os.path.exists(fallback_file):
                    lang_file = fallback_file

        try:
            with open(lang_file, "rb") as f:
                self._translations[language] = self._flatten_dict(tomli.load(f))
            return True
        except (FileNotFoundError, tomli.TOMLDecodeError):
            # Fallback to English
            self._plugin.logger.warning(
                f"Could not load translations for '{language}', falling back to English"
            )
            return self.load_language("en")

    def _flatten_dict(
        self, data: dict[str, Any], parent_key: str = ""
    ) -> dict[str, str]:
        """Flatten nested dictionary to dot notation.

        Args:
            data: Nested dictionary
            parent_key: Parent key prefix

        Returns:
            Flattened dictionary
        """
        items: list[tuple[str, str]] = []

        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key).items())
            elif isinstance(value, str):
                items.append((new_key, value))
            else:
                items.append((new_key, str(value)))

        return dict(items)

    def translate(self, key: str, **kwargs: Any) -> str:
        """Translate a key with optional formatting.

        Args:
            key: Translation key
            **kwargs: Formatting arguments

        Returns:
            Translated string
        """
        # Get translations for current language
        lang_translations = self._translations.get(self._current_language, {})

        # Try to find the translation
        translation = lang_translations.get(key, key)

        # Fallback to English if not found
        if translation == key:
            en_translations = self._translations.get("en", {})
            translation = en_translations.get(key, key)

        # Format the translation with provided arguments
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError):
            # Return unformatted translation if formatting fails
            return translation

    def set_language(self, language: str) -> None:
        """Set the current language.

        Args:
            language: Language code
        """
        self._current_language = language

    def get_available_languages(self) -> list[str]:
        """Get list of available languages.

        Returns:
            List of available language codes
        """
        languages: list[str] = []

        if os.path.exists(self._translations_dir):
            for filename in os.listdir(self._translations_dir):
                if filename.endswith(".toml"):
                    lang_code = filename[:-5]  # Remove .toml
                    languages.append(lang_code)

        return sorted(languages)

    def reload(self, language: str | None = None) -> None:
        """Reload translations.

        Args:
            language: Specific language to reload, or None for all
        """
        if language:
            self.load_language(language)
        else:
            # Reload all loaded languages
            for lang in self._translations.keys():
                self.load_language(lang)
