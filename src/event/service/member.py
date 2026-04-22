from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.models.member import MemberORM
from event.schema.member import (
    MemberCreate,
    MemberPatch,
    MemberPut,
    MemberRead,
)
from event.uow.member import MemberUOW

logger = getLogger(__name__)


class MemberService(BaseService[MemberUOW]):
    @required_transaction
    async def _create(self, member_create: MemberCreate) -> MemberORM:
        member_data = member_create.model_dump()
        roles = member_data.pop("roles", [])
        return await self.uow.members.create_member_with_roles(
            member_data=member_data, role_ids=roles
        )

    @required_transaction
    async def _read(self, member_id: UUID) -> MemberORM | None:
        member = await self.uow.members.get_by_id(member_id)
        return member

    @required_transaction
    async def _update(
        self, member_id: UUID, member_data: dict, *, flush: bool = False
    ) -> MemberORM:
        member = await self.uow.members.update_one(
            member_id, member_data, flush
        )
        return member

    @required_transaction
    async def _delete(self, member_id: UUID) -> None:
        await self.uow.members.delete_one(member_id)

    async def create(self, member_create: MemberCreate) -> MemberRead:
        async with self.uow as uow:
            member = await self._create(member_create)
            result = MemberRead.model_validate(member)
            await uow.commit()
        return result

    async def read(self, member_id: UUID) -> MemberRead:
        async with self.uow:
            member = await self._read(member_id)
            return MemberRead.model_validate(member)

    async def patch(self, member_patch: MemberPatch) -> MemberRead:
        async with self.uow as uow:
            member_data = member_patch.model_dump(exclude_unset=True)
            member = await self._update(member_patch.id, member_data)
            result = MemberRead.model_validate(member)
            await uow.commit()
        return result

    async def put(self, member_put: MemberPut) -> MemberRead:
        async with self.uow as uow:
            member_data = member_put.model_dump()
            member_id = member_data.pop("id")
            member = await self._update(member_id, member_data)
            result = MemberRead.model_validate(member)
            await uow.commit()
        return result

    async def delete(self, member_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(member_id)
            await uow.commit()
