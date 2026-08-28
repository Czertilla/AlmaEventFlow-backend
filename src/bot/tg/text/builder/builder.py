import logging
from enum import Enum

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.text.localization import i18n_manager
from core.config.settings import settings

from .account import AccountMixin
from .menu import MenuMixin

DEFAULT_MARKUP: str = settings.BOT_PARSE_MODE

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TextBuilder(MenuMixin, AccountMixin):
    """A class responsible for constructing localized message texts with
    appropriate markup formatting.
    """

    def __init__(
        self, lang: str | None = None, markup: str = DEFAULT_MARKUP.value
    ) -> None:
        """
        Initializes a TextBuilder instance.

        Args:
            lang (str | None, optional): The language for the message.
                Defaults to None (falls back to default).
            markup (str, optional): The markup format for messages.
                Defaults to `DEFAULT_MARKUP`.
        """
        self.lang: str | None = (
            lang if settings.LOCALIZATION_AVAILABLE else None
        )
        self.markup: str = markup
        logger.debug(f"initialized TextBuilder(lang={lang}, markup={markup})")

    async def get_username_warning(self) -> str:
        return await self.get_phrase(LocaleKey.Error.username, ch=Emoji.warning)

    async def get_phrase(self, key: str | Enum, **kwargs) -> str:
        """
        Retrieves a localized phrase asynchronously.

        Args:
            key (str): The key identifier for the phrase.
            **kwargs: Additional parameters for formatting.

        Returns:
            str: The localized and formatted phrase.
        """
        if isinstance(key, Enum):
            key = str(key.value)
        phrase = await i18n_manager.get(key, self.lang, self.markup, **kwargs)
        logger.debug(
            f"fetched phrase for key='{key}' with kwargs={kwargs}: '{phrase}'"
        )
        return phrase

    async def get_lang_title(self, ch=None) -> str:
        return await self.get_phrase(
            LocaleKey.title,
            ch=ch or Emoji.get_lang_emoji(self.lang),
        )

    async def add_button(self, char: Emoji = Emoji.heavy_plus_sign) -> str:
        return await self.get_phrase(LocaleKey.Button.add, ch=char)

    async def delete_button(self, char: Emoji = Emoji.x) -> str:
        return await self.get_phrase(LocaleKey.Button.delete, ch=char)

    async def unlink_button(self, char: Emoji = Emoji.x) -> str:
        return await self.get_phrase(LocaleKey.Button.unlink, ch=char)

    async def notifications_button(self, char: Emoji = Emoji.bell) -> str:
        return await self.get_phrase(LocaleKey.Button.notifications, ch=char)

    async def cancel_button(self, char: Emoji = Emoji.x) -> str:
        return await self.get_phrase(LocaleKey.Button.cancel, ch=char)

    async def confirm_button(
        self, char: Emoji = Emoji.ballot_box_with_check
    ) -> str:
        return await self.get_phrase(LocaleKey.Button.confirm, ch=char)

    async def back_button(self, char: Emoji = Emoji.arrow_backward) -> str:
        return await self.get_phrase(LocaleKey.Button.back, ch=char)

    async def system_button(self, char: Emoji = Emoji.gear) -> str:
        return await self.get_phrase(
            LocaleKey.Menu.Language.Items.sys,
            ch=char,
        )

    async def user_not_found_error(self) -> str:
        return await self.get_phrase(LocaleKey.Error.user_not_found)
