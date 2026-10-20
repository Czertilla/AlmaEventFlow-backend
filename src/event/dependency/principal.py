from uuid import UUID

from fastapi import Depends

from core.dependencies.auth import UserJWTDep
from core.dto.base import dto_from_orm
from core.schema.error import ErrorCode
from core.schema.user import UserJWT
from core.utils.exc.http import VancedHTTPException
from event.dependency.attendance import AttendanceUOWDep
from event.dependency.collective import CollectiveUOWDep
from event.dependency.member import MemberUOWDep
from event.dependency.participation import ParticipationUOWDep
from event.dependency.role import RoleUOWDep
from event.dto.principal import CollectivePrincipalDTO, MemberIdentityDTO
from event.exc.event import (
    AttendanceNotExistsException,
    CollectiveNotExistsException,
    MemberNotExistsException,
    ParticipationNotExistsException,
    RoleNotExistsException,
)


async def verify_collective_principal(
    collective_id: UUID,
    user: UserJWTDep,
    collective_uow: CollectiveUOWDep,
) -> tuple[CollectivePrincipalDTO, UserJWT]:
    async with collective_uow as uow:
        collective = await uow.collectives.get_by_id(collective_id)
        if not collective:
            raise CollectiveNotExistsException()
        if not user.is_superuser and user.person_id != collective.principal_id:
            raise VancedHTTPException(
                status_code=403, detail=ErrorCode.NOT_COLLECTIVE_PRINCIPAL
            )
    return dto_from_orm(collective, CollectivePrincipalDTO), user


async def verify_member_person(
    member_id: UUID,
    user: UserJWTDep,
    member_uow: MemberUOWDep,
) -> tuple[MemberIdentityDTO, UserJWT]:
    async with member_uow as uow:
        member = await uow.members.get_by_id(member_id)
        if not member:
            raise MemberNotExistsException()
        if not user.is_superuser and user.person_id != member.person_id:
            raise VancedHTTPException(
                status_code=403, detail=ErrorCode.NOT_MEMBER_PERSON
            )
    return dto_from_orm(member, MemberIdentityDTO), user


type PrincipalOf = tuple[CollectivePrincipalDTO, UserJWT]


async def verify_member_of_collective(
    collective_id: UUID,
    member_id: UUID,
    uow: MemberUOWDep,
    principal: PrincipalOf = Depends(verify_collective_principal),
) -> PrincipalOf:
    """The principal acts only on members of their own collective."""
    async with uow:
        member = await uow.members.get_by_id(member_id)
    if member is None or member.collective_id != collective_id:
        raise MemberNotExistsException()
    return principal


async def verify_role_of_collective(
    collective_id: UUID,
    role_id: UUID,
    uow: RoleUOWDep,
    principal: PrincipalOf = Depends(verify_collective_principal),
) -> PrincipalOf:
    async with uow:
        role = await uow.roles.get_by_id(role_id)
    if role is None or role.collective_id != collective_id:
        raise RoleNotExistsException()
    return principal


async def verify_attendance_of_collective(
    collective_id: UUID,
    attendance_id: UUID,
    uow: AttendanceUOWDep,
    principal: PrincipalOf = Depends(verify_collective_principal),
) -> PrincipalOf:
    async with uow:
        owner = await uow.attendances.collective_id_of(attendance_id)
    if owner != collective_id:
        raise AttendanceNotExistsException()
    return principal


async def verify_participation_of_collective(
    collective_id: UUID,
    participation_id: UUID,
    uow: ParticipationUOWDep,
    principal: PrincipalOf = Depends(verify_collective_principal),
) -> PrincipalOf:
    async with uow:
        participation = await uow.participations.get_by_id(participation_id)
    if participation is None or participation.collective_id != collective_id:
        raise ParticipationNotExistsException()
    return principal
