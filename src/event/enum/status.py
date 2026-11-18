from enum import StrEnum, auto


class EventStatusEnumV1(StrEnum):
    draft = auto()
    template = auto()
    planned = auto()
    active = auto()
    archived = auto()
