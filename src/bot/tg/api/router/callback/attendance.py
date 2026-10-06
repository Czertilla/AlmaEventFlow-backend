from logging import getLogger
from uuid import UUID

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from aiogram.utils.callback_answer import CallbackAnswer

from bot.enum.locales import LocaleKey
from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.enum.callbacks import AttendanceCB
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.utils.aef_client import (
    AefClientError,
    get_my_attendance,
    patch_my_attendance,
)
from bot.tg.utils.deeplink import start_url

router = Router(name="attendance/")
logger = getLogger(__name__)


@router.callback_query(AttendanceCB.filter())
async def mark_attendance(
    callback: CallbackQuery,
    callback_data: AttendanceCB,
    callback_answer: CallbackAnswer,
    user: TGUser,
    bot: Bot,
    uow: AccountLinkUOWDep,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    phrase = text_builder.get_phrase
    callback_answer.show_alert = True

    person_id = await AccountLinkService(uow).get_person_id(user.id)
    if person_id is None:
        callback_answer.text = await phrase(LocaleKey.Attendance.need_link)
        callback_answer.url = await start_url(bot)
        return

    event_id = callback_data.event_id
    try:
        attendances = await get_my_attendance(person_id, event_id)
    except AefClientError:
        logger.exception("attendance lookup failed for person %s", person_id)
        callback_answer.text = await phrase(LocaleKey.Attendance.unavailable)
        return
    if not attendances:
        callback_answer.text = await phrase(LocaleKey.Attendance.not_participant)
        return

    attendance = attendances[0]
    is_going = callback_data.decision == "yes"
    try:
        await patch_my_attendance(
            person_id,
            UUID(attendance["member_id"]),
            UUID(attendance["id"]),
            is_attended=is_going,
        )
    except AefClientError:
        logger.exception(
            "attendance patch failed for person %s, event %s",
            person_id,
            event_id,
        )
        callback_answer.text = await phrase(LocaleKey.Attendance.save_error)
        return

    callback_answer.show_alert = False
    callback_answer.text = await phrase(
        LocaleKey.Attendance.yes if is_going else LocaleKey.Attendance.no
    )
