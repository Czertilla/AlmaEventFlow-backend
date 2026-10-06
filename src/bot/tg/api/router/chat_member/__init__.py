from logging import getLogger

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import (
    ADMINISTRATOR,
    IS_MEMBER,
    IS_NOT_MEMBER,
    MEMBER,
    ChatMemberUpdatedFilter,
)
from aiogram.types import ChatMemberUpdated, Message

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.collective_chat import ChatBindingDTO
from bot.tg.service.actor import ActorService
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.service.user import TelegramUserService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.uow.message import TelegramMessageUOW
from bot.tg.uow.user import UserUOW
from bot.tg.utils.html import html_escape

router = Router(name="chat_member/")
logger = getLogger(__name__)

GROUPS = F.chat.type.in_({"group", "supergroup"})
PRIVATE = F.chat.type == "private"


def _chats(bot: Bot) -> CollectiveChatService:
    return CollectiveChatService(CollectiveChatUOW(), bot)


async def _say(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except TelegramAPIError:
        logger.info("could not post to chat %s", chat_id, exc_info=True)


@router.my_chat_member(GROUPS, ChatMemberUpdatedFilter(IS_NOT_MEMBER >> MEMBER))
async def added_as_member(event: ChatMemberUpdated, bot: Bot) -> None:
    logger.info("bot added to chat %s by %s", event.chat.id, event.from_user.id)
    text = await TextBuilder(event.from_user.language_code).get_phrase(
        LocaleKey.Group.bot_added
    )
    await _say(bot, event.chat.id, text)


@router.my_chat_member(
    GROUPS, ChatMemberUpdatedFilter(MEMBER >> ADMINISTRATOR)
)
async def promoted(event: ChatMemberUpdated, bot: Bot) -> None:
    text = await TextBuilder(event.from_user.language_code).get_phrase(
        LocaleKey.Group.bot_promoted
    )
    await _say(bot, event.chat.id, text)


@router.my_chat_member(
    GROUPS, ChatMemberUpdatedFilter(ADMINISTRATOR >> MEMBER)
)
async def demoted(event: ChatMemberUpdated, bot: Bot) -> None:
    binding = await _chats(bot).get_binding(event.chat.id)
    if binding is None:
        return
    logger.warning(
        "bot lost admin rights in chat %s of collective %s",
        event.chat.id,
        binding.collective_id,
    )
    text = await TextBuilder(event.from_user.language_code).get_phrase(
        LocaleKey.Group.bot_demoted
    )
    await _say(bot, event.chat.id, text)


async def _tell_leader(bot: Bot, binding: ChatBindingDTO) -> None:
    service = TelegramUserService(UserUOW())
    leader = await service.get_user(binding.set_by_id)
    if leader is None:
        return
    name = str(binding.collective_id)
    try:
        actor = await ActorService(AccountLinkUOW()).resolve(leader)
        known = actor.led_collective(binding.collective_id)
        name = known.name if known is not None else name
    except Exception:
        logger.warning("could not resolve the leader of %s", name, exc_info=True)
    text = await TextBuilder(leader.language_code).get_phrase(
        LocaleKey.Group.released, ch=Emoji.warning, collective=html_escape(name)
    )
    await _say(bot, binding.set_by_id, text)


@router.my_chat_member(
    GROUPS, ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER)
)
async def removed(event: ChatMemberUpdated, bot: Bot) -> None:
    binding = await _chats(bot).release_chat(event.chat.id)
    if binding is not None:
        logger.warning(
            "bot removed from chat %s, collective %s released",
            event.chat.id,
            binding.collective_id,
        )
        await _tell_leader(bot, binding)


@router.my_chat_member(
    PRIVATE, ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER)
)
async def blocked(event: ChatMemberUpdated) -> None:
    await TelegramUserService(UserUOW()).set_active(event.from_user.id, False)


@router.my_chat_member(
    PRIVATE, ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER)
)
async def unblocked(event: ChatMemberUpdated) -> None:
    await TelegramUserService(UserUOW()).set_active(event.from_user.id, True)


@router.message(F.migrate_to_chat_id)
async def migrated(message: Message, bot: Bot) -> None:
    new_chat_id = message.migrate_to_chat_id
    if new_chat_id is None:
        return
    await _chats(bot).move_chat(message.chat.id, new_chat_id)
    async with TelegramMessageUOW() as uow:
        await uow.messages.move_chat(message.chat.id, new_chat_id)
        await uow.commit(True)
    logger.info("chat %s migrated to %s, bindings moved", message.chat.id, new_chat_id)
