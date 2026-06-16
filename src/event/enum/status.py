from enum import StrEnum, auto


class EventStatusEnumV1(StrEnum):
    draft = auto()
    template = auto()
    active = auto()
    archived = auto()
