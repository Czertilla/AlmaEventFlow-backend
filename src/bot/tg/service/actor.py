import asyncio
from collections.abc import Awaitable
from logging import getLogger
from typing import Any
from uuid import UUID

from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import CollectiveRefDTO
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.utils.aef_client import (
    AefClientError,
    get_my_collectives,
    get_my_memberships,
)
from core.service.base import BaseService

logger = getLogger(__name__)


def _refs(rows: list[dict[str, Any]]) -> tuple[CollectiveRefDTO, ...]:
    return tuple(
        sorted(
            (
                CollectiveRefDTO(
                    id=UUID(str(row["id"])), name=row.get("name") or str(row["id"])
                )
                for row in rows
            ),
            key=lambda item: item.name,
        )
    )


class ActorService(BaseService[AccountLinkUOW]):
    """Works out who a Telegram user is to the platform: not linked at all,
    linked but attached to nothing, a member, or a collective leader. Link
    state is local; the collectives come from ``event`` and a failure there
    only blanks that part (``roles_known``), it never blocks the bot."""

    async def resolve(self, user: TGUser) -> ActorDTO:
        person_id = await AccountLinkService(self.uow).get_person_id(user.id)
        if person_id is None:
            return ActorDTO(tg_id=user.id, is_superuser=bool(user.is_superuser))
        led, member_of = await asyncio.gather(
            self._safe(get_my_collectives(person_id), person_id),
            self._safe(get_my_memberships(person_id), person_id),
        )
        return ActorDTO(
            tg_id=user.id,
            person_id=person_id,
            is_superuser=bool(user.is_superuser),
            led=_refs(led or []),
            member_of=_refs(member_of or []),
            roles_known=led is not None and member_of is not None,
        )

    @staticmethod
    async def _safe(
        call: Awaitable[list[dict[str, Any]]], person_id: UUID
    ) -> list[dict[str, Any]] | None:
        try:
            return await call
        except (AefClientError, TimeoutError):
            logger.warning(
                "collectives lookup failed for person %s", person_id, exc_info=True
            )
            return None
