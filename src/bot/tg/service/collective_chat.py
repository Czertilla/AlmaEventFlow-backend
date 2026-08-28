from logging import getLogger
from uuid import UUID

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.utils.aef_client import get_my_collectives
from core.service.base import BaseService

logger = getLogger(__name__)

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


class NotBotAdminError(Exception):
    """The bot isn't an admin in the target chat (yet)."""


class NoLedCollectiveError(Exception):
    """The caller doesn't lead (isn't principal of) any collective."""


class AmbiguousCollectiveError(Exception):
    """The caller leads more than one collective; needs an explicit pick.
    Carries (id, name) pairs so the caller can offer a labelled choice
    (button, prompt, ...) instead of raw ids."""

    def __init__(self, collectives: list[tuple[UUID, str]]) -> None:
        super().__init__("ambiguous collective")
        self.collectives = collectives


class CollectiveChatService(BaseService[CollectiveChatUOW]):
    """Binds a Telegram group chat to a collective as its official
    announcements chat. Gated by two independent checks: the bot must
    already be an admin in the chat (so it can post/edit later), and the
    caller must be that collective's principal (per ``GET /me/collectives``,
    which already scopes to collectives the caller leads)."""

    def __init__(self, uow: CollectiveChatUOW, bot: Bot) -> None:
        super().__init__(uow)
        self.bot = bot

    async def setup(
        self,
        person_id: UUID,
        chat_id: int,
        set_by_id: int,
        *,
        collective_id: UUID | None = None,
        thread_id: int | None = None,
    ) -> UUID:
        await self._require_bot_admin(chat_id)
        resolved = await self._resolve_collective(person_id, collective_id)
        async with self.uow as uow:
            row = await uow.collective_chats.upsert(
                resolved, chat_id, set_by_id, thread_id=thread_id
            )
            await uow.commit(True)
        logger.info(
            "chat %s bound to collective %s by tg user %s",
            chat_id,
            resolved,
            set_by_id,
        )
        return row.collective_id

    async def disable(self, person_id: UUID, chat_id: int) -> bool:
        """Unbinds this chat, if the caller still leads the collective it was
        bound to. Returns whether anything was removed."""
        led_ids = {cid for cid, _ in await self._led_collectives(person_id)}
        async with self.uow as uow:
            existing = await uow.collective_chats.get_by_chat_id(chat_id)
            if existing is None or existing.collective_id not in led_ids:
                return False
            await uow.collective_chats.delete_one(existing.id)
            await uow.commit(True)
        return True

    async def _require_bot_admin(self, chat_id: int) -> None:
        me = await self.bot.get_me()
        member = await self.bot.get_chat_member(chat_id, me.id)
        if member.status not in _ADMIN_STATUSES:
            raise NotBotAdminError()

    async def _led_collectives(self, person_id: UUID) -> list[tuple[UUID, str]]:
        collectives = await get_my_collectives(person_id)
        return [
            (UUID(str(c["id"])), c.get("name") or str(c["id"]))
            for c in collectives
        ]

    async def _resolve_collective(
        self, person_id: UUID, collective_id: UUID | None
    ) -> UUID:
        led = await self._led_collectives(person_id)
        led_ids = {cid for cid, _ in led}
        if not led_ids:
            raise NoLedCollectiveError()
        if collective_id is not None:
            if collective_id not in led_ids:
                raise NoLedCollectiveError()
            return collective_id
        if len(led_ids) == 1:
            return next(iter(led_ids))
        raise AmbiguousCollectiveError(sorted(led, key=lambda item: item[1]))
