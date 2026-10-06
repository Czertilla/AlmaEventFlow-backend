from functools import lru_cache
from logging import getLogger
from typing import Any

from aiogram.types import (
    BotCommand,
    BotCommandScope,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from bot.enum.locales import Locale
from bot.tg.dto.actor import ActorDTO, ActorState
from bot.tg.text.locales_data import locales_data
from core.config.settings import settings

logger = getLogger(__name__)

PRIVATE_SCOPE_BY_STATE = {
    ActorState.unlinked: "private_unlinked",
    ActorState.linked: "private_linked",
    ActorState.member: "private_linked",
    ActorState.leader: "private_leader",
}


@lru_cache
def command_sets() -> dict[str, dict[str, dict[str, str]]]:
    data = locales_data()
    return {
        locale.value: data.get(locale.value, {}).get("_commands", {})
        for locale in Locale
    }


def language_variants() -> list[tuple[str | None, str]]:
    """(``language_code`` for Telegram, locale of the texts). The last entry
    has no language code, so it serves every language the bot has no
    translation for."""
    variants: list[tuple[str | None, str]] = [
        (locale.value, locale.value) for locale in Locale
    ]
    variants.append((None, settings.LOCALIZATION_DEFAULT_LANG))
    return variants


def _commands(locale: str, *scopes: str) -> list[BotCommand]:
    sets = command_sets().get(locale, {})
    merged: dict[str, str] = {}
    for scope in scopes:
        merged |= sets.get(scope, {})
    return [
        BotCommand(command=name, description=description)
        for name, description in merged.items()
    ]


def _hint(
    scope: BotCommandScope, language_code: str | None, commands: list[BotCommand]
) -> dict[str, Any]:
    return {"scope": scope, "language_code": language_code, "commands": commands}


def static_hints() -> list[dict[str, Any]]:
    scopes: dict[str, tuple[BotCommandScope, tuple[str, ...]]] = {
        "default": (BotCommandScopeDefault(), ("default",)),
        "all_private_chats": (
            BotCommandScopeAllPrivateChats(),
            ("private_unlinked",),
        ),
        "all_group_chats": (BotCommandScopeAllGroupChats(), ("all_group_chats",)),
        "all_chat_administrators": (
            BotCommandScopeAllChatAdministrators(),
            ("all_chat_administrators",),
        ),
    }
    return [
        _hint(scope, code, _commands(locale, *names))
        for code, locale in language_variants()
        for scope, names in scopes.values()
    ]


def private_scope_names(actor: ActorDTO) -> tuple[str, ...]:
    names = (PRIVATE_SCOPE_BY_STATE[actor.state],)
    return (*names, "private_superuser") if actor.is_superuser else names


def user_hints(actor: ActorDTO) -> list[dict[str, Any]]:
    scope = BotCommandScopeChat(chat_id=actor.tg_id)
    names = private_scope_names(actor)
    return [
        _hint(scope, code, _commands(locale, *names))
        for code, locale in language_variants()
    ]
