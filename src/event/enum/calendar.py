from enum import StrEnum, auto


class CalendarSubscriptionTypeEnum(StrEnum):
    personal_all = auto()
    personal_collective = auto()
    principal_collective = auto()


class CalendarChangeTypeEnum(StrEnum):
    removed = auto()
    archived = auto()
