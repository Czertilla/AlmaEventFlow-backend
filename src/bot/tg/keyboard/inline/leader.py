from enum import Enum
from uuid import UUID

from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import ChatBindingDTO
from bot.tg.enum.callbacks import (
    CBPrefix,
    LeaderAction,
    LeaderCB,
    SetupAction,
    SetupCB,
)
from bot.tg.utils.abstract.keyboard_builder import ABCKeyboardBuilder


class LeaderMixin(ABCKeyboardBuilder[InlineKeyboardButton]):
    async def _back_button(self, target_callback: str) -> InlineKeyboardButton:
        raise NotImplementedError()

    async def leader_list_kb(
        self, actor: ActorDTO, bound: set[UUID], *, back: bool
    ) -> InlineKeyboardMarkup:
        for item in actor.led:
            marker = (
                Emoji.white_check_mark
                if item.id in bound
                else Emoji.heavy_plus_sign
            )
            self.row(
                InlineKeyboardButton(
                    text=f"{marker} {item.name}"[:64],
                    callback_data=LeaderCB(
                        action=LeaderAction.card, collective_id=item.id
                    ).pack(),
                )
            )
        if back:
            self.row(await self._back_button(CBPrefix.back))
        return self.inline()

    async def _toggle(
        self,
        key: Enum,
        state: str,
        action: LeaderAction,
        collective_id: UUID,
    ) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=await self.text_builder.get_phrase(key, state=state),
            callback_data=LeaderCB(
                action=action, collective_id=collective_id
            ).pack(),
        )

    async def leader_card_kb(
        self,
        collective_id: UUID,
        binding: ChatBindingDTO | None,
        bind_url: str,
        default_lang: str,
    ) -> InlineKeyboardMarkup:
        phrase = self.text_builder.get_phrase
        if binding is not None:
            state = self.text_builder.state_label
            self.row(
                await self._toggle(
                    LocaleKey.Button.announce,
                    await state(binding.announce_enabled),
                    LeaderAction.announce,
                    collective_id,
                ),
                await self._toggle(
                    LocaleKey.Button.silent,
                    await state(binding.silent),
                    LeaderAction.silent,
                    collective_id,
                ),
            )
            self.row(
                await self._toggle(
                    LocaleKey.Button.pin,
                    await state(binding.pin_announcements),
                    LeaderAction.pin,
                    collective_id,
                ),
                await self._toggle(
                    LocaleKey.Button.language,
                    await self.text_builder.lang_label(
                        binding.language or default_lang
                    ),
                    LeaderAction.language,
                    collective_id,
                ),
            )
        self.row(
            InlineKeyboardButton(
                text=await phrase(LocaleKey.Button.bind_group),
                url=bind_url,
                style=ButtonStyle.PRIMARY if binding is None else None,
            )
        )
        if binding is not None:
            self.row(
                InlineKeyboardButton(
                    text=await phrase(LocaleKey.Button.unbind),
                    callback_data=LeaderCB(
                        action=LeaderAction.unbind, collective_id=collective_id
                    ).pack(),
                    style=ButtonStyle.DANGER,
                )
            )
        self.row(
            await self._back_button(LeaderCB(action=LeaderAction.list).pack())
        )
        return self.inline()

    async def setup_pick_kb(
        self, collectives: list[tuple[UUID, str]]
    ) -> InlineKeyboardMarkup:
        for collective_id, name in collectives:
            self.row(
                InlineKeyboardButton(
                    text=name[:64],
                    callback_data=SetupCB(
                        action=SetupAction.pick, collective_id=collective_id
                    ).pack(),
                )
            )
        return self.inline()

    async def setup_replace_kb(self, target_id: UUID) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.cancel_button(),
                callback_data=SetupCB(action=SetupAction.cancel).pack(),
            ),
            InlineKeyboardButton(
                text=await self.text_builder.get_phrase(LocaleKey.Button.replace),
                callback_data=SetupCB(
                    action=SetupAction.swap, collective_id=target_id
                ).pack(),
                style=ButtonStyle.SUCCESS,
            ),
        )
        return self.inline()

    async def url_kb(
        self, key: Enum, url: str, *, primary: bool = True
    ) -> InlineKeyboardMarkup:
        self.row(
            InlineKeyboardButton(
                text=await self.text_builder.get_phrase(key),
                url=url,
                style=ButtonStyle.PRIMARY if primary else None,
            )
        )
        return self.inline()

