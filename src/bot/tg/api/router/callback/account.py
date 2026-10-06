from logging import getLogger

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.callback_answer import CallbackAnswer

from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.actor import ActorDep
from bot.tg.dependency.usecase.account import AccountStateUserUseCaseDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.service.actor import ActorService
from bot.tg.service.commands import CommandMenuService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.usecase.account import AccountUseCase
from bot.tg.utils.aef_client import (
    AefClientError,
    get_telegram_notifications_enabled,
    set_telegram_notifications_enabled,
)
from bot.tg.utils.message import edit_message
from bot.tg.utils.notifications import notifications_state

router = Router(name="account/")
router.callback_query.filter(F.message.chat.type == "private")
logger = getLogger(__name__)


@router.callback_query(F.data == CBPrefix.account)
async def account(
    callback: CallbackQuery, actor: ActorDep, usecase: AccountStateUserUseCaseDep
):
    await edit_message(
        callback,
        await usecase.on_account(actor, await notifications_state(actor)),
    )


@router.callback_query(F.data == CBPrefix.account_unlink)
async def account_unlink_confirm(
    callback: CallbackQuery, usecase: AccountStateUserUseCaseDep
):
    await edit_message(callback, await usecase.on_confirm_unlink())


@router.callback_query(F.data == CBPrefix.account_unlink / "yes")
async def account_unlink(
    callback: CallbackQuery,
    callback_answer: CallbackAnswer,
    user: TGUser,
    bot: Bot,
    uow: AccountLinkUOWDep,
    state: FSMContext,
):
    updated = await AccountLinkService(uow).unlink(user.id)
    text_builder = TextBuilder(lang=user.language_code)
    refreshed = await ActorService(AccountLinkUOW()).resolve(updated or user)
    await CommandMenuService(bot).refresh(refreshed)
    usecase = AccountUseCase(text_builder, user=updated or user, state=state)
    callback_answer.text = await text_builder.on_unlinked()
    await edit_message(callback, await usecase.on_account(refreshed, None))


@router.callback_query(F.data == CBPrefix.account_notify)
async def account_toggle_notifications(
    callback: CallbackQuery,
    callback_answer: CallbackAnswer,
    actor: ActorDep,
    usecase: AccountStateUserUseCaseDep,
    user: TGUser,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    if actor.person_id is None:
        callback_answer.text = await text_builder.on_notifications_error()
        return
    try:
        currently_enabled = await get_telegram_notifications_enabled(
            actor.person_id
        )
        await set_telegram_notifications_enabled(
            actor.person_id, not currently_enabled
        )
    except AefClientError:
        logger.exception(
            "failed to toggle telegram notifications for person %s",
            actor.person_id,
        )
        callback_answer.text = await text_builder.on_notifications_error()
        callback_answer.show_alert = True
        return
    callback_answer.text = await text_builder.on_notifications_toggled(
        not currently_enabled
    )
    await edit_message(
        callback, await usecase.on_account(actor, not currently_enabled)
    )
