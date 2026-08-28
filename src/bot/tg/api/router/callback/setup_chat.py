from logging import getLogger
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.collective_chat import CollectiveChatUOWDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.service.collective_chat import (
    CollectiveChatService,
    NoLedCollectiveError,
    NotBotAdminError,
)
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils.aef_client import AefClientError

router = Router(name="setup_chat/")
router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))

logger = getLogger(__name__)


@router.callback_query(F.data.startswith(f"{CBPrefix.setup_chat}/"))
async def setup_chat_pick(
    callback: CallbackQuery,
    user: TGUser,
    account_uow: AccountLinkUOWDep,
    chat_uow: CollectiveChatUOWDep,
    bot: Bot,
) -> None:
    """Handles a tap on one of the collective-name buttons offered by
    ``/setup_chat`` when the caller leads more than one. Re-validates the
    pick against the tapping user's own led collectives exactly like the
    typed-id path did -- a different group member tapping the same button
    simply gets rejected by that check, no extra bookkeeping needed."""
    text_builder = TextBuilder(lang=user.language_code)
    try:
        collective_id = UUID((callback.data or "").split("/", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    person_id = await AccountLinkService(account_uow).get_person_id(user.id)
    if person_id is None:
        await callback.answer(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.not_linked, ch=Emoji.warning
            ),
            show_alert=True,
        )
        return

    service = CollectiveChatService(chat_uow, bot)
    try:
        await service.setup(
            person_id,
            callback.message.chat.id,
            user.id,
            collective_id=collective_id,
        )
    except NotBotAdminError:
        await callback.answer(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.not_admin, ch=Emoji.warning
            ),
            show_alert=True,
        )
        return
    except NoLedCollectiveError:
        await callback.answer(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.no_collective, ch=Emoji.warning
            ),
            show_alert=True,
        )
        return
    except AefClientError:
        logger.exception(
            "collective lookup failed for person %s in chat %s",
            person_id,
            callback.message.chat.id,
        )
        await callback.answer(
            await text_builder.get_phrase(
                LocaleKey.SetupChat.error, ch=Emoji.warning
            ),
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        await text_builder.get_phrase(
            LocaleKey.SetupChat.success, ch=Emoji.white_check_mark
        )
    )
    await callback.answer()
