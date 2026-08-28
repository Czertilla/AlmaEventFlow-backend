from enum import StrEnum


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
    setup_chat = "SC"

    def __truediv__(self, other):
        return self + "/" + str(other)
