import json
import logging
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import aiocache
import i18n

from core.config.settings import settings

logger = logging.getLogger(__name__)


class Localization:
    """
    Handles localization and caching for translated strings.

    Attributes:
        cache (aiocache.Cache): cache instanse
        TTL (int): default Time-to-live for cached translations from settings
            Defaults to `LOCALIZATION_CACHE_TTL` from settings
    """

    cache: aiocache.RedisCache = aiocache.Cache.from_url(settings.REDIS_URL)
    TTL: int = settings.LOCALIZATION_CACHE_TTL
    DEFAULT_LANG = settings.LOCALIZATION_DEFAULT_LANG

    def __init__(
        self,
        default_lang: str = DEFAULT_LANG,
        ttl: int = TTL,
    ) -> None:
        """
        Initializes the Localization instance.

        Args:
            default_lang (str, optional): Default language for translations.
                Defaults to "en".
            ttl (int, optional): Time-to-live for cached translations.
                Defaults to `TTL` attribute.
        """
        self.default_lang: str = default_lang
        self.translations_path: Path = Path() / "res/locales"
        self.ttl: int = ttl

        i18n.config.set("load_path", [str(self.translations_path)])
        i18n.config.set("fallback", self.default_lang)

        logger.info(f"Localization initialized: {self}")

    def __repr__(self) -> str:
        """
        Returns a string representation of the Localization instance.

        Returns:
            str: A formatted string containing the class name, default
                language, and TTL.
        """
        return (
            f"<Localization(default_lang={self.default_lang}, ttl={self.ttl})>"
        )

    @staticmethod
    def hash_kwargs(kwargs: dict) -> str:
        """
        Creates a SHA256 hash from the passed dictionary, previously by
        sorting keys and processing UUID values.

        Args:
            kwargs (dict): A dictionary with hashing data.

        Returns:
            str: SHA-256 hash as a string.
        """
        filtered_kwargs = {
            k: (v.__hash__() if isinstance(v, UUID) else v)
            for k, v in kwargs.items()
        }
        return sha256(
            json.dumps(filtered_kwargs, sort_keys=True).encode()
        ).hexdigest()

    async def get(
        self,
        key: str,
        lang: str | None = None,
        markup: str = "HTML",
        **kwargs: Any,
    ) -> str:
        """
        Retrieves a localized string asynchronously. Uses caching to improve
        performance.

        Args:
            key (str): The translation key.
            lang (str, optional): The language for the translation.
                Defaults to `None`, which falls back to `default_lang`.
            markup (str, optional): The format for the translation key.
                Defaults to "HTML".
            **kwargs (Any): Additional parameters for formatting.

        Returns:
            str: The translated string.
        """
        lang = lang or self.default_lang
        cache_key = f"i18n:{lang}:{key}:{self.hash_kwargs(kwargs)}"

        # Check cache
        cached_translation: str | None = await self.cache.get(cache_key)
        if cached_translation:
            logger.debug(f"Cache hit: {cache_key}")
            return cached_translation

        # Load translation if cache miss
        logger.debug(f"Cache miss: {cache_key}. Fetching translation.")

        text: str = i18n.t(f"{markup}.{key}", locale=lang, **kwargs)

        # Store in cache
        await self.cache.set(cache_key, text, ttl=self.ttl, namespace="i18n")
        logger.debug(f"Cached translation: {cache_key} (TTL: {self.ttl}s)")

        return text


# Global localization object
i18n_manager: Localization = Localization()
