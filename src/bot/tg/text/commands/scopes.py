from enum import StrEnum, auto
from logging import getLogger

from aiogram.types import (
    BotCommandScope,
    BotCommandScopeChat,
    BotCommandScopeUnion,
)

from bot.tg.uow.user import UserUOW
from core.utils.typing import iter_union, unwrap_literal

logger = getLogger(__name__)


class CustomScope(StrEnum):
    superuser = auto()


async def get_superusers_scopes():
    async with UserUOW() as uow:
        return [
            BotCommandScopeChat(chat_id=tgid)
            for tgid in (await uow.users.get_all_superusers_tg_id())
        ]


def get_scopes_task(scope: CustomScope):
    match scope:
        case CustomScope.superuser:
            return get_superusers_scopes()
        case default:
            raise ValueError(f"Invalid custom scope: {default}")


async def get_custom_scopes(scope: CustomScope):
    return await get_scopes_task(scope)


def get_scope_types():
    scopes = {
        unwrap_literal(type_field.annotation): scope_type
        for scope_type in iter_union(BotCommandScopeUnion)
        if issubclass(scope_type, BotCommandScope)
        and (type_field := scope_type.model_fields.get("type")) is not None
    }
    logger.debug(f"Got {scopes=}")
    return scopes
