from logging import getLogger

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.usecase.account import AccountStateUserUseCaseDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.usecase.account import AccountUseCase
from bot.tg.utils.aef_client import (
    AefClientError,
    get_telegram_notifications_enabled,
    set_telegram_notifications_enabled,
)

router = Router(name="account/")
router.callback_query.filter(F.message.chat.type == "private")
logger = getLogger(__name__)


@router.callback_query(F.data == CBPrefix.account)
async def account(callback: CallbackQuery, usecase: AccountStateUserUseCaseDep):
    await callback.message.edit_text(**await usecase.on_account())


@router.callback_query(F.data == CBPrefix.account_unlink)
async def account_unlink_confirm(
    callback: CallbackQuery, usecase: AccountStateUserUseCaseDep
):
    await callback.message.edit_text(**await usecase.on_confirm_unlink())


@router.callback_query(F.data == CBPrefix.account_unlink / "yes")
async def account_unlink(
    callback: CallbackQuery,
    user: TGUser,
    uow: AccountLinkUOWDep,
    state: FSMContext,
):
    updated = await AccountLinkService(uow).unlink(user.id)
    text_builder = TextBuilder(lang=user.language_code)
    usecase = AccountUseCase(text_builder, user=updated or user, state=state)
    await callback.answer(await text_builder.on_unlinked())
    await callback.message.edit_text(**await usecase.on_account())


@router.callback_query(F.data == CBPrefix.account_notify)
async def account_toggle_notifications(
    callback: CallbackQuery,
    user: TGUser,
    uow: AccountLinkUOWDep,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    person_id = await AccountLinkService(uow).get_person_id(user.id)
    if person_id is None:
        await callback.answer(await text_builder.on_notifications_error())
        return
    try:
        currently_enabled = await get_telegram_notifications_enabled(person_id)
        await set_telegram_notifications_enabled(
            person_id, not currently_enabled
        )
    except AefClientError:
        logger.exception(
            "failed to toggle telegram notifications for person %s",
            person_id,
        )
        await callback.answer(await text_builder.on_notifications_error())
        return
    await callback.answer(
        await text_builder.on_notifications_toggled(not currently_enabled),
        show_alert=True,
    )
