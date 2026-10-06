from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from aiogram.enums import ChatMemberStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

BOT_ID = 777
CHAT = -1001234567890
LEADER_TG = 11


def _uow(bot_engine: AsyncEngine) -> Any:
    from bot.tg.uow.collective_chat import CollectiveChatUOW

    return CollectiveChatUOW(async_sessionmaker(bot_engine, expire_on_commit=False))


class FakeBot:
    def __init__(self, admins: set[int] | None = None) -> None:
        self.admins = {BOT_ID, LEADER_TG} if admins is None else admins

    async def get_me(self) -> Any:
        return SimpleNamespace(id=BOT_ID)

    async def get_chat_member(self, chat_id: int, user_id: int) -> Any:
        status = (
            ChatMemberStatus.ADMINISTRATOR
            if user_id in self.admins
            else ChatMemberStatus.MEMBER
        )
        return SimpleNamespace(status=status)


def _service(bot_engine: AsyncEngine, bot: FakeBot | None = None) -> Any:
    from bot.tg.service.collective_chat import CollectiveChatService

    return CollectiveChatService(_uow(bot_engine), cast(Any, bot or FakeBot()))


@pytest.fixture
def leads(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[UUID, str]]]:
    registry: dict[str, list[tuple[UUID, str]]] = {}

    async def fake(person_id: UUID) -> list[dict[str, Any]]:
        return [
            {"id": str(cid), "name": name}
            for cid, name in registry.get(str(person_id), [])
        ]

    monkeypatch.setattr("bot.tg.service.collective_chat.get_my_collectives", fake)
    return registry


async def test_database_rejects_a_chat_bound_to_two_collectives(
    bot_engine: AsyncEngine,
) -> None:
    async with _uow(bot_engine) as uow:
        await uow.collective_chats.upsert(uuid4(), CHAT, 1)
        await uow.commit(True)

    with pytest.raises(IntegrityError):
        async with _uow(bot_engine) as uow:
            await uow.collective_chats.upsert(uuid4(), CHAT, 2)
            await uow.commit(True)


async def test_another_leader_cannot_take_a_chat_that_is_already_official(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import ChatAlreadyBoundError

    first_person, second_person = uuid4(), uuid4()
    first, second = uuid4(), uuid4()
    leads[str(first_person)] = [(first, "Chess club")]
    leads[str(second_person)] = [(second, "Rival club")]
    service = _service(bot_engine, FakeBot({BOT_ID, 11, 12}))

    await service.setup(first_person, CHAT, 11)
    with pytest.raises(ChatAlreadyBoundError) as raised:
        await service.setup(second_person, CHAT, 12)

    assert raised.value.collective_id == first
    assert raised.value.led_by_caller is False
    assert raised.value.collective_name is None
    binding = await service.get_binding(CHAT)
    assert binding is not None and binding.collective_id == first


async def test_leader_of_both_collectives_can_replace_the_binding_explicitly(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import ChatAlreadyBoundError

    person = uuid4()
    first, second = uuid4(), uuid4()
    leads[str(person)] = [(first, "Alpha"), (second, "Beta")]
    service = _service(bot_engine)

    await service.setup(person, CHAT, LEADER_TG, collective_id=first)
    with pytest.raises(ChatAlreadyBoundError) as raised:
        await service.setup(person, CHAT, LEADER_TG, collective_id=second)
    assert raised.value.led_by_caller is True
    assert raised.value.collective_name == "Alpha"

    result = await service.setup(
        person, CHAT, LEADER_TG, collective_id=second, replace=True
    )

    assert result.changed is True
    assert result.collective_name == "Beta"
    assert await service.get_binding_of_collective(first) is None
    binding = await service.get_binding(CHAT)
    assert binding is not None and binding.collective_id == second


async def test_repeating_setup_for_the_same_chat_changes_nothing(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)

    first = await service.setup(person, CHAT, LEADER_TG)
    again = await service.setup(person, CHAT, LEADER_TG)

    assert first.changed is True
    assert again.changed is False
    assert again.moved_from_chat_id is None


async def test_moving_a_collective_to_another_chat_frees_the_old_one(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    other_chat = CHAT - 1

    await service.setup(person, CHAT, LEADER_TG)
    moved = await service.setup(person, other_chat, LEADER_TG)

    assert moved.moved_from_chat_id == CHAT
    assert await service.get_binding(CHAT) is None
    other = await service.get_binding(other_chat)
    assert other is not None and other.collective_id == collective


async def test_only_chat_administrators_may_bind_a_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import NotChatAdminError

    person = uuid4()
    leads[str(person)] = [(uuid4(), "Chess club")]
    service = _service(bot_engine, FakeBot({BOT_ID}))

    with pytest.raises(NotChatAdminError):
        await service.setup(person, CHAT, LEADER_TG)

    assert await service.get_binding(CHAT) is None


async def test_the_bot_must_be_an_administrator_to_bind_a_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import NotBotAdminError

    person = uuid4()
    leads[str(person)] = [(uuid4(), "Chess club")]
    service = _service(bot_engine, FakeBot({LEADER_TG}))

    with pytest.raises(NotBotAdminError):
        await service.setup(person, CHAT, LEADER_TG)


async def test_a_person_without_collectives_cannot_bind_a_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import NoLedCollectiveError

    service = _service(bot_engine)

    with pytest.raises(NoLedCollectiveError):
        await service.setup(uuid4(), CHAT, LEADER_TG)


async def test_a_leader_of_several_collectives_must_choose_one(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    from bot.tg.service.collective_chat import AmbiguousCollectiveError

    person = uuid4()
    first, second = uuid4(), uuid4()
    leads[str(person)] = [(second, "Beta"), (first, "Alpha")]
    service = _service(bot_engine)

    with pytest.raises(AmbiguousCollectiveError) as raised:
        await service.setup(person, CHAT, LEADER_TG)

    assert [name for _, name in raised.value.collectives] == ["Alpha", "Beta"]


async def test_only_the_collective_leader_can_unbind_the_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, stranger = uuid4(), uuid4()
    leads[str(person)] = [(uuid4(), "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)

    assert await service.disable(stranger, CHAT) is False
    assert await service.get_binding(CHAT) is not None
    assert await service.disable(person, CHAT) is True
    assert await service.get_binding(CHAT) is None


async def test_releasing_a_chat_drops_its_binding_without_ownership_checks(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)

    released = await service.release_chat(CHAT)

    assert released is not None and released.collective_id == collective
    assert await service.release_chat(CHAT) is None


async def test_a_migrated_chat_keeps_its_binding_under_the_new_id(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)
    supergroup = -1009999999999

    await service.move_chat(CHAT, supergroup)

    assert await service.get_binding(CHAT) is None
    moved = await service.get_binding(supergroup)
    assert moved is not None and moved.collective_id == collective


async def test_a_new_binding_announces_loudly_without_pinning(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person = uuid4()
    leads[str(person)] = [(uuid4(), "Chess club")]
    service = _service(bot_engine)

    result = await service.setup(person, CHAT, LEADER_TG)

    binding = result.binding
    assert binding.announce_enabled is True
    assert binding.silent is False
    assert binding.pin_announcements is False
    assert binding.language is None


async def test_a_leader_changes_the_settings_of_their_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)

    updated = await service.update_settings(
        person, collective, {"silent": True, "language": "en"}
    )

    assert updated is not None
    assert updated.silent is True and updated.language == "en"
    stored = await service.get_binding(CHAT)
    assert stored is not None and stored.silent is True


async def test_settings_belong_only_to_the_leader_of_the_collective(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, stranger, collective = uuid4(), uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)

    assert await service.update_settings(stranger, collective, {"silent": True}) is None
    stored = await service.get_binding(CHAT)
    assert stored is not None and stored.silent is False


async def test_unknown_settings_are_rejected(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    service = _service(bot_engine)

    with pytest.raises(ValueError, match="collective_id"):
        await service.update_settings(uuid4(), uuid4(), {"collective_id": None})


async def test_settings_survive_moving_the_collective_to_another_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, collective = uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)
    await service.update_settings(person, collective, {"pin_announcements": True})

    await service.setup(person, CHAT - 1, LEADER_TG)

    moved = await service.get_binding(CHAT - 1)
    assert moved is not None and moved.pin_announcements is True


async def test_bindings_of_several_collectives_are_read_at_once(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person = uuid4()
    first, second = uuid4(), uuid4()
    leads[str(person)] = [(first, "Alpha"), (second, "Beta")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG, collective_id=first)

    found = await service.bindings_of([first, second])

    assert set(found) == {first}
    assert found[first].chat_id == CHAT
    assert await service.bindings_of([]) == {}


async def test_a_leader_unbinds_a_collective_without_being_in_the_chat(
    bot_engine: AsyncEngine, leads: dict[str, list[tuple[UUID, str]]]
) -> None:
    person, stranger, collective = uuid4(), uuid4(), uuid4()
    leads[str(person)] = [(collective, "Chess club")]
    service = _service(bot_engine)
    await service.setup(person, CHAT, LEADER_TG)

    assert await service.unbind_collective(stranger, collective) is None
    removed = await service.unbind_collective(person, collective)

    assert removed is not None and removed.chat_id == CHAT
    assert await service.get_binding(CHAT) is None
    assert await service.unbind_collective(person, collective) is None
