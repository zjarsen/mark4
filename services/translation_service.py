"""Translation service for multi-language support."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('mark4_bot')


class TranslationService:
    """Manages translations with in-memory caching."""

    def __init__(self, database_service, locales_dir: str, default_lang: str = 'zh_CN'):
        """
        Initialize translation service.

        Args:
            database_service: DatabaseService instance
            locales_dir: Path to locales directory containing JSON files
            default_lang: Default language code (default: zh_CN)
        """
        self.db = database_service
        self.locales_dir = Path(locales_dir)
        self.default_lang = default_lang
        self.translations: Dict[str, Dict] = {}
        self._load_all_translations()

    def _load_all_translations(self):
        """Load all translation files into memory."""
        if not self.locales_dir.exists():
            logger.warning(f"Locales directory not found: {self.locales_dir}")
            return

        for json_file in self.locales_dir.glob('*.json'):
            lang_code = json_file.stem
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                logger.info(f"Loaded translations for {lang_code}")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

    def get(self, user_id: int, key: str, **kwargs) -> str:
        """
        Get translated string for user's language with variable substitution.

        Args:
            user_id: Telegram user ID
            key: Translation key using dot notation (e.g., 'welcome.message')
            **kwargs: Variables for string formatting

        Returns:
            Translated string with variables substituted
        """
        user_lang = self.db.get_user_language(user_id)
        text = self._get_translation(user_lang, key)

        # Fallback to default language
        if text is None and user_lang != self.default_lang:
            text = self._get_translation(self.default_lang, key)
            logger.warning(f"Missing translation: {key} in {user_lang}, using {self.default_lang}")

        # Last resort fallback
        if text is None:
            logger.error(f"Missing translation: {key} in all languages")
            text = f"[{key}]"

        # Variable substitution
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable {e} for key {key}")
            return text

    def get_lang(self, lang_code: str, key: str, **kwargs) -> str:
        """
        Get translation for specific language (bypass user preference).

        Args:
            lang_code: Language code (e.g., 'zh_CN', 'en_US')
            key: Translation key using dot notation
            **kwargs: Variables for string formatting

        Returns:
            Translated string with variables substituted
        """
        text = self._get_translation(lang_code, key)

        # Fallback to default language
        if text is None:
            text = self._get_translation(self.default_lang, key)

        # Last resort fallback
        if text is None:
            text = f"[{key}]"

        # Variable substitution
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    def _get_translation(self, lang_code: str, key: str) -> Optional[str]:
        """
        Get translation from cache using dot notation.

        Args:
            lang_code: Language code
            key: Translation key (e.g., 'welcome.message')

        Returns:
            Translated string or None if not found
        """
        if lang_code not in self.translations:
            return None

        keys = key.split('.')
        value = self.translations[lang_code]

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None

        return value if isinstance(value, str) else None

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get list of available languages.

        Returns:
            Dictionary of language codes to language names
        """
        languages = {}
        for lang_code in self.translations.keys():
            lang_name = self._get_translation(lang_code, 'language.name')
            if lang_name:
                languages[lang_code] = lang_name
        return languages
