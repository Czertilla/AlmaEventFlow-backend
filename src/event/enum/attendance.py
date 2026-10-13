from enum import StrEnum, auto


class AttendanceOutcomeEnumV1(StrEnum):
    attended = auto()
    absent = auto()
    unmarked = auto()
    upcoming = auto()
