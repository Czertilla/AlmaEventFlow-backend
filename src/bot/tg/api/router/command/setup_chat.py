from logging import getLogger
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.collective_chat import CollectiveChatUOWDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.service.collective_chat import (
    AmbiguousCollectiveError,
    CollectiveChatService,
    NoLedCollectiveError,
    NotBotAdminError,
)
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils.aef_client import AefClientError

router = Router(name="setup_chat/")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

logger = getLogger(__name__)


@router.message(Command("setup_chat"))
async def setup_chat(
    message: Message,
    command: CommandObject,
    user: TGUser,
    account_uow: AccountLinkUOWDep,
    chat_uow: CollectiveChatUOWDep,
    bot: Bot,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    args = (command.args or "").strip()

    person_id = await AccountLinkService(account_uow).get_person_id(user.id)
    if person_id is None:
        await message.reply(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.not_linked, ch=Emoji.warning
            )
        )
        return

    if args.lower() == "off":
        removed = await CollectiveChatService(chat_uow, bot).disable(
            person_id, message.chat.id
        )
        key = (
            LocaleKey.SetupChat.disabled
            if removed
            else LocaleKey.SetupChat.not_bound
        )
        await message.reply(
            await text_builder.get_phrase(key, ch=Emoji.white_check_mark)
        )
        return

    collective_id: UUID | None = None
    if args:
        try:
            collective_id = UUID(args)
        except ValueError:
            await message.reply(
                await text_builder.get_phrase(
                    LocaleKey.SetupChat.invalid_id, ch=Emoji.warning
                )
            )
            return

    service = CollectiveChatService(chat_uow, bot)
    try:
        await service.setup(
            person_id,
            message.chat.id,
            user.id,
            collective_id=collective_id,
        )
    except NotBotAdminError:
        await message.reply(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.not_admin, ch=Emoji.warning
            )
        )
        return
    except NoLedCollectiveError:
        await message.reply(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.no_collective, ch=Emoji.warning
            )
        )
        return
    except AmbiguousCollectiveError as exc:
        keyboard = InlineKeyboardBuilder()
        for collective_id, name in exc.collectives:
            keyboard.button(
                text=name,
                callback_data=str(CBPrefix.setup_chat / str(collective_id)),
            )
        keyboard.adjust(1)
        await message.reply(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.ambiguous, ch=Emoji.warning
            ),
            reply_markup=keyboard.as_markup(),
        )
        return
    except AefClientError:
        logger.exception(
            "collective lookup failed for person %s in chat %s",
            person_id,
            message.chat.id,
        )
        await message.reply(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.error, ch=Emoji.warning
            )
        )
        return

    await message.reply(
        await text_builder.get_phrase(
            LocaleKey.SetupChat.success, ch=Emoji.white_check_mark
        )
    )
