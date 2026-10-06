from enum import Enum

from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.enum.emoji import Emoji
from bot.enum.locales import Locale, LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.enum.callbacks import CBPrefix, LeaderAction, LeaderCB
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils import links
from bot.tg.utils.abstract.keyboard_builder import ABCKeyboardBuilder


class MenuMixin(ABCKeyboardBuilder[InlineKeyboardButton]):
    async def _back_button(self, target_callback: str) -> InlineKeyboardButton:
        raise NotImplementedError()

    async def _url_button(
        self, key: Enum, emoji: Emoji, url: str
    ) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=await self.text_builder.get_phrase(key, ch=emoji), url=url
        )

    async def main_menu(self, actor: ActorDTO) -> InlineKeyboardMarkup:
        phrase = self.text_builder.get_phrase
        if actor.is_linked:
            self.row(
                InlineKeyboardButton(
                    text=await phrase(
                        LocaleKey.Menu.Main.Items.account,
                        ch=Emoji.bust_in_silhouette,
                    ),
                    callback_data=CBPrefix.account,
                )
            )
            if actor.is_leader:
                self.row(
                    InlineKeyboardButton(
                        text=await phrase(
                            LocaleKey.Menu.Main.Items.collectives,
                            ch=Emoji.busts_in_silhouette,
                        ),
                        callback_data=LeaderCB(action=LeaderAction.list).pack(),
                    )
                )
        else:
            self.row(
                InlineKeyboardButton(
                    text=await phrase(
                        LocaleKey.Menu.Main.Items.link, ch=Emoji.link
                    ),
                    callback_data=CBPrefix.link,
                    style=ButtonStyle.PRIMARY,
                )
            )
        self.row(
            await self._url_button(
                LocaleKey.Menu.Main.Items.site,
                Emoji.globe_with_meridians,
                links.site_url(),
            )
        )
        self.row(
            InlineKeyboardButton(
                text=await phrase(
                    LocaleKey.Menu.Main.Items.lang, ch=Emoji.speech_balloon
                ),
                callback_data=CBPrefix.language,
            ),
            InlineKeyboardButton(
                text=await phrase(
                    LocaleKey.Menu.Main.Items.info, ch=Emoji.information_source
                ),
                callback_data=CBPrefix.info,
            ),
        )
        return self.inline()

    async def link_kb(self, *, back: bool) -> InlineKeyboardMarkup:
        self.row(
            await self._url_button(
                LocaleKey.Button.login, Emoji.key, links.login_url()
            )
        )
        self.row(
            await self._url_button(
                LocaleKey.Button.register, Emoji.memo, links.register_url()
            ),
            await self._url_button(
                LocaleKey.Button.profile,
                Emoji.bust_in_silhouette,
                links.profile_url(),
            ),
        )
        if back:
            self.row(await self._back_button(CBPrefix.back))
        return self.inline()

    async def account_kb(
        self, actor: ActorDTO, notifications_enabled: bool | None
    ) -> InlineKeyboardMarkup:
        if actor.is_linked:
            if notifications_enabled is not None:
                self.row(
                    InlineKeyboardButton(
                        text=await self.text_builder.notifications_button(
                            Emoji.bell
                            if notifications_enabled
                            else Emoji.no_bell
                        ),
                        callback_data=CBPrefix.account_notify,
                    )
                )
            self.row(
                await self._url_button(
                    LocaleKey.Button.profile,
                    Emoji.bust_in_silhouette,
                    links.profile_url(),
                ),
                InlineKeyboardButton(
                    text=await self.text_builder.unlink_button(),
                    callback_data=CBPrefix.account_unlink,
                ),
            )
        else:
            self.row(
                InlineKeyboardButton(
                    text=await self.text_builder.get_phrase(
                        LocaleKey.Menu.Main.Items.link, ch=Emoji.link
                    ),
                    callback_data=CBPrefix.link,
                    style=ButtonStyle.PRIMARY,
                )
            )
        self.row(await self._back_button(CBPrefix.back))
        return self.inline()

    async def account_unlink_confirm_kb(self) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.cancel_button(),
                callback_data=CBPrefix.account,
            ),
            InlineKeyboardButton(
                text=await self.text_builder.confirm_button(),
                callback_data=CBPrefix.account_unlink / "yes",
                style=ButtonStyle.DANGER,
            ),
        )
        return self.inline()

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
        self.row(await self._back_button(CBPrefix.back))
        return self.inline()

    async def back_only_kb(self) -> InlineKeyboardMarkup:
        self.row(await self._back_button(CBPrefix.back))
        return self.inline()

    async def confirm_kb(self, is_danger: bool = False) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.cancel_button(),
                callback_data=CBPrefix.cancel,
            ),
            InlineKeyboardButton(
                text=await self.text_builder.confirm_button(),
                callback_data=CBPrefix.confirm,
                style=ButtonStyle.DANGER if is_danger else ButtonStyle.PRIMARY,
            ),
        )
        return self.inline()
