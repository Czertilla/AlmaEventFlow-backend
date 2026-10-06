from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class CBPrefix(StrEnum):
    back = "back"
    cancel = "cancel"
    confirm = "confirm"

    settings = "S"
    language = "S/l"
    info = "I"
    account = "AC"
    account_unlink = "AC/u"
    account_notify = "AC/n"
    link = "LK"

    def __truediv__(self, other):
        return self + "/" + str(other)


class LeaderAction(StrEnum):
    list = "list"
    card = "card"
    announce = "announce"
    silent = "silent"
    pin = "pin"
    detail = "detail"
    language = "lang"
    unbind = "unbind"


class LeaderCB(CallbackData, prefix="ld"):
    action: LeaderAction
    collective_id: UUID | None = None


class SetupAction(StrEnum):
    pick = "pick"
    swap = "swap"
    cancel = "cancel"


class SetupCB(CallbackData, prefix="sc"):
    action: SetupAction
    collective_id: UUID | None = None


class AttendanceCB(CallbackData, prefix="att"):
    event_id: UUID
    decision: str
