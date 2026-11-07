from enum import StrEnum


class Audience(StrEnum):
    PRIVATE = "private"
    CONTEXT = "context"
    ALL_USERS = "all_users"

    @property
    def rank(self) -> int:
        return _RANK[self]


_RANK = {Audience.PRIVATE: 0, Audience.CONTEXT: 1, Audience.ALL_USERS: 2}


def clamp(value: Audience, narrowest: Audience, widest: Audience) -> Audience:
    if value.rank < narrowest.rank:
        return narrowest
    if value.rank > widest.rank:
        return widest
    return value
