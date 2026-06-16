from enum import StrEnum, auto


class EventTypeEnumV1(StrEnum):
    rehearsal = auto()
    competition = auto()
    concert = auto()
    festival = auto()
    play = auto()
    performance = auto()
