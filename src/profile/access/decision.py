from dataclasses import dataclass
from enum import StrEnum


class Via(StrEnum):
    SELF = "self"
    SUPERUSER = "superuser"
    AUDIENCE = "audience"
    GRANT = "grant"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Decision:
    allow: bool
    via: Via
    reason_code: str | None = None

    @classmethod
    def granted(cls, via: Via) -> "Decision":
        return cls(True, via)

    @classmethod
    def refused(cls, reason_code: str) -> "Decision":
        return cls(False, Via.NONE, reason_code)
