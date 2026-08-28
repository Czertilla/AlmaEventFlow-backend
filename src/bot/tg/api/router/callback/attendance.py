from logging import getLogger
from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.service.account_link import AccountLinkService
from bot.tg.utils.aef_client import (
    AefClientError,
    get_my_attendance,
    patch_my_attendance,
)

router = Router(name="attendance/")
logger = getLogger(__name__)


@router.callback_query(F.data.startswith("att:"))
async def mark_attendance(
    callback: CallbackQuery, uow: AccountLinkUOWDep
) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        return
    _, event_id_raw, decision = parts
    try:
        event_id = UUID(event_id_raw)
    except ValueError:
        return

    person_id = await AccountLinkService(uow).get_person_id(
        callback.from_user.id
    )
    if person_id is None:
        await callback.answer(
            "Сначала привяжите Telegram к аккаунту AlmaEventFlow: /account",
            show_alert=True,
        )
        return

    try:
        attendances = await get_my_attendance(person_id, event_id)
    except AefClientError:
        logger.exception("attendance lookup failed for person %s", person_id)
        await callback.answer(
            "Не удалось получить данные. Попробуйте позже.", show_alert=True
        )
        return
    if not attendances:
        await callback.answer(
            "Не нашли ваше участие в этом мероприятии.", show_alert=True
        )
        return

    attendance = attendances[0]
    try:
        await patch_my_attendance(
            person_id,
            UUID(attendance["member_id"]),
            UUID(attendance["id"]),
            is_attended=(decision == "yes"),
        )
    except AefClientError:
        logger.exception(
            "attendance patch failed for person %s, event %s",
            person_id,
            event_id,
        )
        await callback.answer(
            "Не удалось сохранить отметку. Попробуйте позже.", show_alert=True
        )
        return

    text = "Отмечено: буду ✅" if decision == "yes" else "Отмечено: не буду ❌"
    await callback.answer(text)
