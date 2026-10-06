from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from aiogram import Bot

from core.config.settings import settings

GROUP_RIGHTS = ("pin_messages",)

_usernames: dict[int, str] = {}


class StartKind(StrEnum):
    onboard = "onboard"
    bind = "bind"
    lead = "lead"


@dataclass(frozen=True, slots=True)
class StartPayload:
    kind: StartKind
    collective_id: UUID | None = None


def encode_start(kind: StartKind, collective_id: UUID | None = None) -> str:
    if kind is StartKind.onboard:
        return StartKind.onboard.value
    if collective_id is None:
        raise ValueError(f"{kind} needs a collective id")
    return f"{kind.value}_{collective_id.hex}"


def parse_start(arg: str | None) -> StartPayload | None:
    """``None`` for anything that is not one of our own payloads, which the
    caller then treats as an account-link code."""
    if not arg:
        return None
    if arg == StartKind.onboard:
        return StartPayload(StartKind.onboard)
    kind, _, rest = arg.partition("_")
    if kind in (StartKind.bind, StartKind.lead) and len(rest) == 32:
        try:
            return StartPayload(StartKind(kind), UUID(hex=rest))
        except ValueError:
            return None
    return None


async def bot_username(bot: Bot) -> str:
    if settings.BOT_TG_USERNAME:
        return settings.BOT_TG_USERNAME
    if bot.id not in _usernames:
        me = await bot.get_me()
        _usernames[bot.id] = me.username or ""
    return _usernames[bot.id]


async def start_url(bot: Bot, payload: str = StartKind.onboard.value) -> str:
    return f"https://t.me/{await bot_username(bot)}?start={payload}"


async def startgroup_url(
    bot: Bot, payload: str, rights: tuple[str, ...] = GROUP_RIGHTS
) -> str:
    url = f"https://t.me/{await bot_username(bot)}?startgroup={payload}"
    return f"{url}&admin={'+'.join(rights)}" if rights else url
