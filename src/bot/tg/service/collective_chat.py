from logging import getLogger
from uuid import UUID

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import IntegrityError

from bot.tg.dto.collective_chat import (
    ChatBindingDTO,
    ChatInfoDTO,
    CollectiveRefDTO,
    SetupResultDTO,
)
from bot.tg.model.collective_chat import CollectiveChatORM
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.utils.aef_client import get_my_collectives
from core.service.base import BaseService

logger = getLogger(__name__)

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


class NotBotAdminError(Exception):
    """The bot isn't an admin in the target chat (yet)."""


class NotChatAdminError(Exception):
    """The caller isn't an administrator of the target chat, so they can't
    decide which collective the chat belongs to."""


class NoLedCollectiveError(Exception):
    """The caller doesn't lead (isn't principal of) any collective."""


class AmbiguousCollectiveError(Exception):
    """The caller leads more than one collective; needs an explicit pick.
    Carries (id, name) pairs so the caller can offer a labelled choice
    (button, prompt, ...) instead of raw ids."""

    def __init__(self, collectives: list[tuple[UUID, str]]) -> None:
        super().__init__("ambiguous collective")
        self.collectives = collectives


class ChatAlreadyBoundError(Exception):
    """The chat is already the official chat of another collective. The name
    is only known when the caller leads that collective too, in which case
    they may replace the binding explicitly in favour of ``target``."""

    def __init__(
        self,
        collective_id: UUID,
        collective_name: str | None,
        *,
        led_by_caller: bool,
        target: CollectiveRefDTO | None = None,
    ) -> None:
        super().__init__(f"chat already bound to {collective_id}")
        self.collective_id = collective_id
        self.collective_name = collective_name
        self.led_by_caller = led_by_caller
        self.target = target


def _binding(row: CollectiveChatORM) -> ChatBindingDTO:
    return ChatBindingDTO(
        collective_id=row.collective_id,
        chat_id=row.chat_id,
        thread_id=row.thread_id,
        set_by_id=row.set_by_id,
        announce_enabled=row.announce_enabled,
        silent=row.silent,
        pin_announcements=row.pin_announcements,
        language=row.language,
    )


SETTING_FIELDS = frozenset(
    {"announce_enabled", "silent", "pin_announcements", "language"}
)


class CollectiveChatService(BaseService[CollectiveChatUOW]):
    """Binds a Telegram group chat to a collective as its official
    announcements chat, one-to-one: a collective has at most one official
    chat and a chat belongs to at most one collective. Gated by three
    independent checks: the bot must already be an admin in the chat (so it
    can post/edit later), the caller must be an administrator of that chat,
    and the caller must be that collective's principal (per
    ``GET /me/collectives``, which already scopes to collectives the caller
    leads)."""

    def __init__(self, uow: CollectiveChatUOW, bot: Bot) -> None:
        super().__init__(uow)
        self.bot = bot

    async def led_collectives(self, person_id: UUID) -> list[CollectiveRefDTO]:
        collectives = await get_my_collectives(person_id)
        return sorted(
            (
                CollectiveRefDTO(
                    id=UUID(str(c["id"])), name=c.get("name") or str(c["id"])
                )
                for c in collectives
            ),
            key=lambda item: item.name,
        )

    async def setup(
        self,
        person_id: UUID,
        chat_id: int,
        set_by_id: int,
        *,
        collective_id: UUID | None = None,
        thread_id: int | None = None,
        replace: bool = False,
    ) -> SetupResultDTO:
        await self._require_bot_admin(chat_id)
        await self._require_chat_admin(chat_id, set_by_id)
        led = await self.led_collectives(person_id)
        target = self._pick(led, collective_id)
        led_names = {item.id: item.name for item in led}

        occupant: CollectiveChatORM | None = None
        result: SetupResultDTO | None = None
        try:
            async with self.uow as uow:
                occupant = await uow.collective_chats.get_by_chat_id(chat_id)
                blocked = (
                    occupant is not None
                    and occupant.collective_id != target.id
                    and not (replace and occupant.collective_id in led_names)
                )
                if not blocked:
                    if occupant is not None and (
                        occupant.collective_id != target.id
                    ):
                        await uow.collective_chats.delete_one(occupant.id)
                    current = await uow.collective_chats.get_by_collective_id(
                        target.id
                    )
                    unchanged = (
                        current is not None
                        and current.chat_id == chat_id
                        and current.thread_id == thread_id
                    )
                    moved_from = (
                        current.chat_id
                        if current is not None and current.chat_id != chat_id
                        else None
                    )
                    row = await uow.collective_chats.upsert(
                        target.id, chat_id, set_by_id, thread_id=thread_id
                    )
                    await uow.commit(True)
                    result = SetupResultDTO(
                        binding=_binding(row),
                        collective_name=target.name,
                        changed=not unchanged,
                        moved_from_chat_id=moved_from,
                    )
        except IntegrityError:
            logger.warning(
                "chat %s was claimed concurrently while binding collective %s",
                chat_id,
                target.id,
            )
            occupant = await self._occupant(chat_id)
            result = None

        if result is None:
            if occupant is None:
                raise ChatAlreadyBoundError(
                    target.id, None, led_by_caller=False, target=target
                )
            raise ChatAlreadyBoundError(
                occupant.collective_id,
                led_names.get(occupant.collective_id),
                led_by_caller=occupant.collective_id in led_names,
                target=target,
            )
        if result.changed:
            logger.info(
                "chat %s bound to collective %s by tg user %s",
                chat_id,
                target.id,
                set_by_id,
            )
        return result

    async def disable(self, person_id: UUID, chat_id: int) -> bool:
        """Unbinds this chat, if the caller still leads the collective it was
        bound to. Returns whether anything was removed."""
        led_ids = {item.id for item in await self.led_collectives(person_id)}
        async with self.uow as uow:
            existing = await uow.collective_chats.get_by_chat_id(chat_id)
            if existing is None or existing.collective_id not in led_ids:
                return False
            await uow.collective_chats.delete_one(existing.id)
            await uow.commit(True)
        return True

    async def release_chat(self, chat_id: int) -> ChatBindingDTO | None:
        """Drops whatever binding the chat has, with no ownership check. For
        events that already prove the chat is gone for the bot (kicked,
        removed), where nobody can be asked."""
        async with self.uow as uow:
            existing = await uow.collective_chats.get_by_chat_id(chat_id)
            if existing is None:
                return None
            binding = _binding(existing)
            await uow.collective_chats.delete_one(existing.id)
            await uow.commit(True)
        logger.info(
            "chat %s released from collective %s", chat_id, binding.collective_id
        )
        return binding

    async def move_chat(self, old_chat_id: int, new_chat_id: int) -> None:
        async with self.uow as uow:
            await uow.collective_chats.move_chat(old_chat_id, new_chat_id)
            await uow.commit(True)

    async def bindings_of(
        self, collective_ids: list[UUID]
    ) -> dict[UUID, ChatBindingDTO]:
        async with self.uow as uow:
            rows = await uow.collective_chats.get_by_collective_ids(
                collective_ids
            )
            return {row.collective_id: _binding(row) for row in rows}

    async def update_settings(
        self,
        person_id: UUID,
        collective_id: UUID,
        changes: dict[str, bool | str | None],
    ) -> ChatBindingDTO | None:
        """Changes the announcement settings of a collective's chat, if the
        caller leads that collective and a chat is bound. ``None`` otherwise."""
        unknown = set(changes) - SETTING_FIELDS
        if unknown:
            raise ValueError(f"unknown chat settings: {sorted(unknown)}")
        led_ids = {item.id for item in await self.led_collectives(person_id)}
        if collective_id not in led_ids:
            return None
        async with self.uow as uow:
            row = await uow.collective_chats.update_settings(
                collective_id, changes
            )
            if row is None:
                return None
            await uow.commit(True)
            return _binding(row)

    async def unbind_collective(
        self, person_id: UUID, collective_id: UUID
    ) -> ChatBindingDTO | None:
        led_ids = {item.id for item in await self.led_collectives(person_id)}
        if collective_id not in led_ids:
            return None
        async with self.uow as uow:
            row = await uow.collective_chats.get_by_collective_id(collective_id)
            if row is None:
                return None
            binding = _binding(row)
            await uow.collective_chats.delete_one(row.id)
            await uow.commit(True)
        return binding

    async def describe_chat(self, chat_id: int) -> ChatInfoDTO | None:
        try:
            chat = await self.bot.get_chat(chat_id)
        except TelegramAPIError:
            return None
        try:
            await self._require_bot_admin(chat_id)
        except (NotBotAdminError, TelegramAPIError):
            return ChatInfoDTO(title=chat.title, bot_is_admin=False)
        return ChatInfoDTO(title=chat.title, bot_is_admin=True)

    async def get_binding(self, chat_id: int) -> ChatBindingDTO | None:
        row = await self._occupant(chat_id)
        return _binding(row) if row is not None else None

    async def get_binding_of_collective(
        self, collective_id: UUID
    ) -> ChatBindingDTO | None:
        async with self.uow as uow:
            row = await uow.collective_chats.get_by_collective_id(collective_id)
            return _binding(row) if row is not None else None

    async def _occupant(self, chat_id: int) -> CollectiveChatORM | None:
        async with self.uow as uow:
            return await uow.collective_chats.get_by_chat_id(chat_id)

    async def _require_bot_admin(self, chat_id: int) -> None:
        me = await self.bot.get_me()
        member = await self.bot.get_chat_member(chat_id, me.id)
        if member.status not in _ADMIN_STATUSES:
            raise NotBotAdminError()

    async def _require_chat_admin(self, chat_id: int, tg_user_id: int) -> None:
        member = await self.bot.get_chat_member(chat_id, tg_user_id)
        if member.status not in _ADMIN_STATUSES:
            raise NotChatAdminError()

    @staticmethod
    def _pick(
        led: list[CollectiveRefDTO], collective_id: UUID | None
    ) -> CollectiveRefDTO:
        if not led:
            raise NoLedCollectiveError()
        if collective_id is not None:
            for item in led:
                if item.id == collective_id:
                    return item
            raise NoLedCollectiveError()
        if len(led) == 1:
            return led[0]
        raise AmbiguousCollectiveError([(item.id, item.name) for item in led])
