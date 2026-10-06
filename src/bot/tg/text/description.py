from dataclasses import dataclass
from functools import lru_cache
from logging import getLogger
from typing import Any

from bot.enum.locales import Locale
from bot.tg.text.commands import language_variants
from bot.tg.text.locales_data import locales_data

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BotProfileText:
    language_code: str | None
    description: str
    short_description: str


@lru_cache
def get_bot_profile_texts() -> list[BotProfileText]:
    data = locales_data()
    known = {locale.value for locale in Locale}
    texts: list[BotProfileText] = []
    for code, locale in language_variants():
        if locale not in known:
            continue
        current: dict[str, Any] = data.get(locale, {})
        texts.append(
            BotProfileText(
                language_code=code,
                description=current.get("description", ""),
                short_description=current.get("short_description", ""),
            )
        )
    return texts
