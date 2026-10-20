from logging import getLogger
from profile.api.kafka.pub.person import on_person_link_changed
from profile.exc.account import PersonAlreadyHasAccountException
from profile.exc.person import PersonNotExistsException
from profile.exc.user import AccountAlreadyLinkedException
from profile.uow.person import PersonUOW
from time import monotonic
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from core.enum.profile import PersonLinkSource
from core.schema.message.profile import PersonLinkData
from core.schema.user import UserJWT
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)

REANNOUNCE_INTERVAL = 30.0
_announced: dict[UUID, float] = {}


class PersonAccountService(BaseService[PersonUOW]):
    @required_transaction
    async def _person_of(self, user_id: UUID) -> UUID | None:
        link = await self.uow.account_links.get_by_user(user_id)
        return link.person_id if link is not None else None

    @required_transaction
    async def _link(
        self,
        user_id: UUID,
        person_id: UUID,
        *,
        replace: bool,
        source: PersonLinkSource,
        actor_id: UUID | None,
    ) -> None:
        if not await self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()
        holder = await self.uow.account_links.get_by_person(person_id)
        if holder is not None and holder.user_id != user_id:
            raise PersonAlreadyHasAccountException()
        current = await self.uow.account_links.get_by_user(user_id)
        if current is not None:
            if current.person_id == person_id:
                return
            if not replace:
                raise AccountAlreadyLinkedException()
            await self.uow.account_links.delete_by_person(current.person_id)
        await self.uow.account_links.add_one(
            {"person_id": person_id, "user_id": user_id}
        )
        await self.uow.account_history.record(
            user_id,
            old_person_id=current.person_id if current is not None else None,
            new_person_id=person_id,
            source=source,
            actor_id=actor_id,
        )

    async def person_of(self, user_id: UUID) -> UUID | None:
        async with self.uow:
            return await self._person_of(user_id)

    async def link(
        self,
        user_id: UUID,
        person_id: UUID,
        *,
        source: PersonLinkSource,
        actor_id: UUID | None = None,
        replace: bool = False,
    ) -> None:
        try:
            async with self.uow as uow:
                await self._link(
                    user_id,
                    person_id,
                    replace=replace,
                    source=source,
                    actor_id=actor_id,
                )
                await uow.commit()
        except IntegrityError as exc:
            raise AccountAlreadyLinkedException() from exc
        await self.announce(user_id)

    async def announce(self, user_id: UUID) -> None:
        person_id = await self.person_of(user_id)
        await on_person_link_changed(
            [PersonLinkData(user_id=user_id, person_id=person_id)]
        )

    async def resolve(self, user: UserJWT) -> UUID | None:
        person_id = await self.person_of(user.id)
        if person_id is not None and person_id != user.person_id:
            await self.reannounce(user.id)
        return person_id

    async def reannounce(self, user_id: UUID) -> None:
        now = monotonic()
        if now - _announced.get(user_id, -REANNOUNCE_INTERVAL) < REANNOUNCE_INTERVAL:
            return
        _announced[user_id] = now
        try:
            await self.announce(user_id)
        except Exception:
            logger.exception("Could not re-announce the link of account %s", user_id)
