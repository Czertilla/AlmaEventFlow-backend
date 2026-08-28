from abc import abstractmethod

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.enum.emoji import Emoji
from bot.enum.locales import Locale, LocaleKey
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils.abstract.keyboard_builder import ABCKeyboardBuilder


class MenuMixin(ABCKeyboardBuilder[InlineKeyboardButton]):
    @abstractmethod
    async def _back_button(self, target_callback: str) -> str:
        raise NotImplementedError()

    async def main_menu(self) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.get_phrase(
                    LocaleKey.Menu.Main.Items.account,
                    ch=Emoji.bust_in_silhouette,
                ),
                callback_data=CBPrefix.account,
            )
        )
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.get_phrase(
                    LocaleKey.Menu.Main.Items.lang,
                    ch=Emoji.globe_with_meridians,
                ),
                callback_data=CBPrefix.language,
            )
        )
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.get_phrase(
                    LocaleKey.Menu.Main.Items.info, ch=Emoji.information_source
                ),
                callback_data=CBPrefix.info,
            )
        )
        return self.as_markup()

    async def account_kb(self, is_linked: bool) -> InlineKeyboardMarkup:
        if is_linked:
            self.row(
                InlineKeyboardButton(
                    text=await self.text_builder.notifications_button(),
                    callback_data=CBPrefix.account_notify,
                )
            )
            self.row(
                InlineKeyboardButton(
                    text=await self.text_builder.unlink_button(),
                    callback_data=CBPrefix.account_unlink,
                )
            )
        self.row(await self._back_button())
        return self.as_markup()

    async def account_unlink_confirm_kb(self) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.cancel_button(),
                callback_data=CBPrefix.account,
            ),
            InlineKeyboardButton(
                text=await self.text_builder.confirm_button(),
                callback_data=CBPrefix.account_unlink / "yes",
                style="danger",
            ),
        )
        return self.as_markup()

    async def language_kb(self) -> InlineKeyboardMarkup:
        for locale in Locale:
            self.row(
                InlineKeyboardButton(
                    text=await TextBuilder(lang=locale.value).get_lang_title(),
                    callback_data=CBPrefix.language / locale.value,
                )
            )
        self.adjust(2)
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.system_button(),
                callback_data=CBPrefix.language / "sys",
            )
        )
        self.row(await self._back_button())
        return self.as_markup()

    async def back_only_kb(self) -> InlineKeyboardMarkup:
        self.row(await self._back_button())
        return self.as_markup()

    async def confirm_kb(self, is_danger: bool = False) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.cancel_button(),
                callback_data=CBPrefix.cancel,
            ),
            InlineKeyboardButton(
                text=await self.text_builder.confirm_button(),
                callback_data=CBPrefix.confirm,
                style="danger" if is_danger else "primary",
            ),
        )
        return self.as_markup()
