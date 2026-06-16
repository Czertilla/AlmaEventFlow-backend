from enum import StrEnum, auto


class EventLevelEnumV1(StrEnum):
    internal = auto()
    regional = auto()
    national = auto()
    international = auto()
