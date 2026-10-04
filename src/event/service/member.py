from logging import getLogger
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from core.dto.base import dto_dict
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.member import (
    MemberCreateDTO,
    MemberDTO,
    MemberFilterDTO,
    MemberPatchDTO,
    MemberPatchRolesDTO,
    MemberPutDTO,
)
from event.dto.role import RolePreviewDTO
from event.exc.event import MemberNotExistsException
from event.filter.member import MemberFilter
from event.models.member import MemberORM, MemberRoleAssociation
from event.models.role import RoleORM
from event.uow.member import MemberUOW

logger = getLogger(__name__)


class MemberService(BaseService[MemberUOW]):
    @staticmethod
    def _to_dto(member: MemberORM) -> MemberDTO:
        return MemberDTO(
            id=member.id,
            collective_id=member.collective_id,
            person_id=member.person_id,
            is_active=member.is_active,
            roles=[
                RolePreviewDTO(id=role.id, name=role.name)
                for role in member.roles
            ],
            created_at=member.created_at,
            edited_at=member.edited_at,
        )

    @required_transaction
    async def _create(self, member_create: MemberCreateDTO) -> MemberORM:
        member_data = dto_dict(member_create, exclude={"roles"})
        return await self.uow.members.create_member_with_roles(
            member_data=member_data, role_ids=member_create.roles
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
        if member is None:
            raise MemberNotExistsException()
        return member

    @required_transaction
    async def _delete(self, member_id: UUID) -> None:
        await self.uow.members.delete_one(member_id)

    @required_transaction
    async def _get_by_person_id(self, person_id: UUID) -> list[MemberORM]:
        return await self.uow.members.get_by_person_id(person_id)

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

    async def create(self, member_create: MemberCreateDTO) -> MemberDTO:
        async with self.uow as uow:
            member = await self._create(member_create)
            result = self._to_dto(member)
            await uow.commit()
        return result

    async def read(self, member_id: UUID) -> MemberDTO:
        async with self.uow:
            member = await self._read(member_id)
            if member is None:
                raise MemberNotExistsException()
            return self._to_dto(member)

    async def patch(self, member_patch: MemberPatchDTO) -> MemberDTO:
        async with self.uow as uow:
            member_data = dto_dict(member_patch, only_set=True)
            member = await self._update(member_patch.id, member_data)
            result = self._to_dto(member)
            await uow.commit()
        return result

    async def patch_roles(
        self, member_id: UUID, patch_data: MemberPatchRolesDTO
    ) -> MemberDTO:
        async with self.uow as uow:
            member = await self._patch_roles(
                member_id, dto_dict(patch_data, only_set=True)
            )
            result = self._to_dto(member)
            await uow.commit()
        return result

    async def put(self, member_put: MemberPutDTO) -> MemberDTO:
        async with self.uow as uow:
            member_data = dto_dict(member_put, exclude={"id"})
            member = await self._update(member_put.id, member_data)
            result = self._to_dto(member)
            await uow.commit()
        return result

    async def delete(self, member_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(member_id)
            await uow.commit()

    async def get_my_members(self, person_id: UUID) -> list[MemberDTO]:
        async with self.uow:
            members = await self._get_by_person_id(person_id)
            return [self._to_dto(m) for m in members]

    async def search(
        self, filter: MemberFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[MemberDTO]:
        async with self.uow as uow:
            orm_filter = MemberFilter.from_dto(filter)
            items, total = await uow.members.search(
                orm_filter,
                page_params,
                options=[selectinload(MemberORM.roles)],
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
