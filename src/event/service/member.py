from logging import getLogger
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from event.exc.event import MemberNotExistsException
from event.filter.member import MemberFilter
from event.models.member import MemberORM, MemberRoleAssociation
from event.models.role import RoleORM
from event.schema.member import (
    MemberCreate,
    MemberPatch,
    MemberPut,
    MemberPatchData,
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
        member = await self.uow.members.get_by_id(
            member_id, options=(selectinload(MemberORM.roles),)
        )
        return member

    @required_transaction
    async def _update(
        self, member_id: UUID, member_data: dict, *, flush: bool = False
    ) -> MemberORM:
        await self.uow.members.update_one(member_id, member_data, flush)
        member = await self.uow.session.scalar(
            select(MemberORM)
            .options(selectinload(MemberORM.roles))
            .where(MemberORM.id == member_id)
        )
        return member

    @required_transaction
    async def _delete(self, member_id: UUID) -> None:
        await self.uow.members.delete_one(member_id)

    @required_transaction
    async def _patch_roles(
        self, member_id: UUID, member_data: dict
    ) -> MemberORM:
        member = await self.uow.members.get_by_id(member_id)
        if not member:
            raise MemberNotExistsException()

        roles = member_data.pop("roles", None)
        if roles is not None:
            await self.uow.session.execute(
                delete(MemberRoleAssociation).where(
                    MemberRoleAssociation.member_id == member_id
                )
            )
            if roles:
                role_objs = (
                    (
                        await self.uow.session.execute(
                            select(RoleORM).where(RoleORM.id.in_(roles))
                        )
                    )
                    .unique()
                    .scalars()
                    .all()
                )
                self.uow.session.add_all(
                    [
                        MemberRoleAssociation(role_id=r.id, member_id=member_id)
                        for r in role_objs
                        if r.collective_id == member.collective_id
                    ]
                )
            await self.uow.session.flush()

        if member_data:
            await self.uow.members.update_one(
                member_id, member_data, flush=False
            )

        member = await self.uow.session.scalar(
            select(MemberORM)
            .options(selectinload(MemberORM.roles))
            .where(MemberORM.id == member_id)
        )
        return member

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
            member_data = member_patch.model_dump()
            member = await self._update(member_patch.id, member_data)
            result = MemberRead.model_validate(member)
            await uow.commit()
        return result

    async def patch_roles(
        self, member_id: UUID, patch_data: MemberPatchData
    ) -> MemberRead:
        async with self.uow as uow:
            member = await self._patch_roles(member_id, patch_data.model_dump())
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

    async def search(
        self, filter: MemberFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[MemberRead]:
        async with self.uow as uow:
            items, total = await uow.members.search(
                filter,
                page_params,
                options=[selectinload(MemberORM.roles)],
            )
            return SPage(
                items=[MemberRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
