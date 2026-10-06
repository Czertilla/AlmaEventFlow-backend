from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import SetupResultDTO
from bot.tg.keyboard.inline import InlineBuilder
from bot.tg.service.collective_chat import (
    AmbiguousCollectiveError,
    ChatAlreadyBoundError,
    CollectiveChatService,
    NoLedCollectiveError,
    NotBotAdminError,
    NotChatAdminError,
)
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils.aef_client import AefClientError
from bot.tg.utils.deeplink import StartKind, encode_start, start_url
from bot.tg.utils.html import html_escape

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatReply:
    """What to say in the group. ``private`` replies are meant for the sender
    only (an ephemeral message where Telegram allows it)."""

    text: str
    markup: InlineKeyboardMarkup | None = None
    private: bool = False


class SetupChatUseCase:
    def __init__(
        self, bot: Bot, service: CollectiveChatService, text_builder: TextBuilder
    ) -> None:
        self.bot = bot
        self.service = service
        self.text_builder = text_builder

    async def _say(
        self,
        key: Enum,
        emoji: Emoji,
        *,
        private: bool = False,
        markup: InlineKeyboardMarkup | None = None,
        **kwargs: str,
    ) -> ChatReply:
        text = await self.text_builder.get_phrase(key, ch=emoji, **kwargs)
        return ChatReply(text, markup, private)

    async def onboarding(self) -> ChatReply:
        markup = await InlineBuilder(self.text_builder).url_kb(
            LocaleKey.Button.start_bot, await start_url(self.bot)
        )
        return await self._say(
            LocaleKey.SetupChat.not_linked,
            Emoji.warning,
            private=True,
            markup=markup,
        )

    async def setup(
        self,
        actor: ActorDTO,
        *,
        chat_id: int,
        thread_id: int | None,
        collective_id: UUID | None = None,
        replace: bool = False,
    ) -> ChatReply:
        if not actor.is_linked or actor.person_id is None:
            return await self.onboarding()
        if actor.roles_known and not actor.is_leader:
            return await self._say(
                LocaleKey.SetupChat.no_collective, Emoji.warning, private=True
            )
        try:
            result = await self.service.setup(
                actor.person_id,
                chat_id,
                actor.tg_id,
                collective_id=collective_id,
                thread_id=thread_id,
                replace=replace,
            )
        except NotBotAdminError:
            return await self._say(LocaleKey.SetupChat.not_admin, Emoji.warning)
        except NotChatAdminError:
            return await self._say(
                LocaleKey.SetupChat.not_chat_admin, Emoji.warning, private=True
            )
        except NoLedCollectiveError:
            return await self._say(
                LocaleKey.SetupChat.no_collective, Emoji.warning, private=True
            )
        except AmbiguousCollectiveError as exc:
            markup = await InlineBuilder(self.text_builder).setup_pick_kb(
                exc.collectives
            )
            return await self._say(
                LocaleKey.SetupChat.ambiguous, Emoji.warning, markup=markup
            )
        except ChatAlreadyBoundError as exc:
            return await self._already_bound(exc)
        except (AefClientError, TelegramAPIError):
            logger.exception(
                "binding chat %s for tg user %s failed", chat_id, actor.tg_id
            )
            return await self._say(
                LocaleKey.SetupChat.error, Emoji.warning, private=True
            )
        return await self._done(result, thread_id is not None)

    async def _already_bound(self, exc: ChatAlreadyBoundError) -> ChatReply:
        if not exc.led_by_caller or exc.target is None:
            return await self._say(
                LocaleKey.SetupChat.already_bound, Emoji.warning, private=True
            )
        markup = await InlineBuilder(self.text_builder).setup_replace_kb(
            exc.target.id
        )
        return await self._say(
            LocaleKey.SetupChat.already_bound_mine,
            Emoji.warning,
            markup=markup,
            current=html_escape(exc.collective_name or ""),
            target=html_escape(exc.target.name),
        )

    async def _done(self, result: SetupResultDTO, in_topic: bool) -> ChatReply:
        name = html_escape(result.collective_name)
        markup = await InlineBuilder(self.text_builder).url_kb(
            LocaleKey.SetupChat.open_settings,
            await start_url(
                self.bot,
                encode_start(StartKind.lead, result.binding.collective_id),
            ),
            primary=False,
            ch=Emoji.gear,
        )
        if not result.changed:
            key = LocaleKey.SetupChat.unchanged
        elif result.moved_from_chat_id is not None:
            key = LocaleKey.SetupChat.moved
        elif in_topic:
            key = LocaleKey.SetupChat.success_topic
        else:
            key = LocaleKey.SetupChat.success
        reply = await self._say(
            key, Emoji.white_check_mark, markup=markup, collective=name
        )
        if result.moved_from_chat_id is not None:
            await self._tell_old_chat(result.moved_from_chat_id, name)
        return reply

    async def _tell_old_chat(self, chat_id: int, collective: str) -> None:
        text = await self.text_builder.get_phrase(
            LocaleKey.SetupChat.old_chat,
            ch=Emoji.information_source,
            collective=collective,
        )
        try:
            await self.bot.send_message(chat_id, text)
        except TelegramAPIError:
            logger.info("could not tell chat %s it was moved", chat_id)

    async def off(self, actor: ActorDTO, chat_id: int) -> ChatReply:
        if not actor.is_linked or actor.person_id is None:
            return await self.onboarding()
        try:
            removed = await self.service.disable(actor.person_id, chat_id)
        except AefClientError:
            logger.exception("unbinding chat %s failed", chat_id)
            return await self._say(
                LocaleKey.SetupChat.error, Emoji.warning, private=True
            )
        if removed:
            return await self._say(
                LocaleKey.SetupChat.disabled, Emoji.white_check_mark
            )
        return await self._say(
            LocaleKey.SetupChat.not_bound, Emoji.warning, private=True
        )

    async def status(self, actor: ActorDTO, chat_id: int) -> ChatReply:
        binding = await self.service.get_binding(chat_id)
        if binding is None:
            return await self._say(
                LocaleKey.SetupChat.status_free, Emoji.information_source
            )
        mine = actor.led_collective(binding.collective_id)
        if mine is None:
            return await self._say(
                LocaleKey.SetupChat.status_bound_other,
                Emoji.information_source,
            )
        return await self._say(
            LocaleKey.SetupChat.status_bound,
            Emoji.information_source,
            collective=html_escape(mine.name),
        )
