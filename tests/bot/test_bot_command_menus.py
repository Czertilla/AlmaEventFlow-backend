from typing import Any
from uuid import uuid4

from aiogram.methods import (
    SetMyCommands,
    SetMyDefaultAdministratorRights,
    SetMyDescription,
    SetMyShortDescription,
)
from aiogram.types import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from bot.tg.dto.actor import ActorDTO, ActorState
from bot.tg.dto.collective_chat import CollectiveRefDTO
from bot.tg.service.commands import CommandMenuService
from bot.tg.text.commands import static_hints, user_hints

PERSON = uuid4()
CLUB = CollectiveRefDTO(uuid4(), "Club")


def names(hint: dict[str, Any]) -> list[str]:
    return [command.command for command in hint["commands"]]


def hint_for(
    hints: list[dict[str, Any]], scope: type, language: str | None
) -> dict[str, Any]:
    return next(
        h
        for h in hints
        if isinstance(h["scope"], scope) and h["language_code"] == language
    )


def test_group_members_see_help_and_only_chat_admins_see_setup() -> None:
    hints = static_hints()

    members = hint_for(hints, BotCommandScopeAllGroupChats, "ru")
    admins = hint_for(hints, BotCommandScopeAllChatAdministrators, "ru")

    assert names(members) == ["help"]
    assert names(admins) == ["help", "setup_chat"]


def test_private_chats_start_with_the_stranger_menu() -> None:
    hints = static_hints()

    private = hint_for(hints, BotCommandScopeAllPrivateChats, "en")
    default = hint_for(hints, BotCommandScopeDefault, "en")

    assert names(private) == ["start", "link", "help", "language"]
    assert "setup_chat" not in names(default)
    assert "account" not in names(default)


def test_every_scope_is_set_for_each_language_and_for_unknown_languages() -> None:
    languages = {hint["language_code"] for hint in static_hints()}

    assert languages == {"en", "ru", None}


def test_descriptions_are_localized() -> None:
    hints = static_hints()

    en = hint_for(hints, BotCommandScopeDefault, "en")["commands"][0]
    ru = hint_for(hints, BotCommandScopeDefault, "ru")["commands"][0]

    assert (en.description, ru.description) == (
        "Open the main menu",
        "Открыть главное меню",
    )


def test_each_role_gets_its_own_complete_private_menu() -> None:
    stranger = ActorDTO(tg_id=1)
    linked = ActorDTO(tg_id=2, person_id=PERSON)
    member = ActorDTO(tg_id=3, person_id=PERSON, member_of=(CLUB,))
    leader = ActorDTO(tg_id=4, person_id=PERSON, led=(CLUB,))
    admin = ActorDTO(tg_id=5, person_id=PERSON, led=(CLUB,), is_superuser=True)

    menus = {
        actor.tg_id: names(hint_for(user_hints(actor), BotCommandScopeChat, "ru"))
        for actor in (stranger, linked, member, leader, admin)
    }

    assert menus[1] == ["start", "link", "help", "language"]
    assert menus[2] == menus[3] == ["start", "account", "help", "language"]
    assert menus[4] == ["start", "account", "collectives", "help", "language"]
    assert menus[5] == [*menus[4], "admin"]
    assert {actor.state for actor in (stranger, linked, member, leader)} == set(
        ActorState
    )


def test_a_user_menu_targets_the_private_chat_of_that_user() -> None:
    hints = user_hints(ActorDTO(tg_id=77))

    assert {hint["scope"].chat_id for hint in hints} == {77}


async def test_the_menu_is_applied_once_per_role(tg: Any) -> None:
    service = CommandMenuService(tg.bot)
    tg.touched.add(900)

    assert await service.refresh(ActorDTO(tg_id=900)) is True
    assert await service.refresh(ActorDTO(tg_id=900)) is False
    assert len(tg.session.of(SetMyCommands)) == 3

    assert await service.refresh(ActorDTO(tg_id=900, person_id=PERSON)) is True
    assert len(tg.session.of(SetMyCommands)) == 6


async def test_a_telegram_failure_does_not_break_the_reply_and_is_retried(
    tg: Any,
) -> None:
    from aiogram.exceptions import TelegramNetworkError

    tg.touched.add(901)
    tg.session.failures[SetMyCommands] = TelegramNetworkError(
        SetMyCommands(commands=[]), "offline"
    )
    service = CommandMenuService(tg.bot)

    assert await service.refresh(ActorDTO(tg_id=901)) is False

    tg.session.failures.clear()
    assert await service.refresh(ActorDTO(tg_id=901)) is True


async def test_startup_sets_every_static_menu_and_the_bot_profile(tg: Any) -> None:
    from bot.tg.app.contextmanager import TGBotContextManager

    manager = TGBotContextManager(bot=tg.bot, dp=None)

    await manager.set_commands()
    await manager.set_profile()

    assert len(tg.session.of(SetMyCommands)) == len(static_hints())
    descriptions = tg.session.of(SetMyDescription)
    shorts = tg.session.of(SetMyShortDescription)
    assert {d.language_code for d in descriptions} == {"en", "ru", None}
    assert all(0 < len(s.short_description) <= 120 for s in shorts)
    rights = tg.session.of(SetMyDefaultAdministratorRights)[0].rights
    assert rights.can_pin_messages is True
    assert rights.can_restrict_members is False


async def test_superusers_get_their_menu_at_startup(tg: Any, bot_seed: Any) -> None:
    from sqlalchemy import update

    from bot.tg.app.contextmanager import TGBotContextManager
    from bot.tg.model.user import TGUserORM

    await bot_seed.tg_user(950)
    async with bot_seed._sessionmaker() as session:
        await session.execute(
            update(TGUserORM).where(TGUserORM.id == 950).values(is_superuser=True)
        )
        await session.commit()
    tg.touched.add(950)

    await TGBotContextManager(bot=tg.bot, dp=None).set_commands()

    admin_menus = [
        [command.command for command in call.commands]
        for call in tg.session.of(SetMyCommands)
        if getattr(call.scope, "chat_id", None) == 950 and call.language_code == "ru"
    ]
    assert admin_menus == [["start", "link", "help", "language", "admin"]]
