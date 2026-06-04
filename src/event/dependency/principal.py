from uuid import UUID

from core.dependencies.auth import UserJWTDep
from core.schema.user import UserJWT
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException
from event.dependency.collective import CollectiveUOWDep
from event.dependency.member import MemberUOWDep
from event.exc.event import CollectiveNotExistsException, MemberNotExistsException
from event.models.collective import CollectiveORM
from event.models.member import MemberORM


async def verify_collective_principal(
    collective_id: UUID,
    user: UserJWTDep,
    collective_uow: CollectiveUOWDep,
) -> tuple[CollectiveORM, UserJWT]:
    async with collective_uow as uow:
        collective = await uow.collectives.get_by_id(collective_id)
        if not collective:
            raise CollectiveNotExistsException()
        if not user.is_superuser and user.person_id != collective.principal_id:
            raise VancedHTTPException(
                status_code=403, detail=ErrorCode.NOT_COLLECTIVE_PRINCIPAL
            )
    return collective, user


async def verify_member_person(
    member_id: UUID,
    user: UserJWTDep,
    member_uow: MemberUOWDep,
) -> tuple[MemberORM, UserJWT]:
    async with member_uow as uow:
        member = await uow.members.get_by_id(member_id)
        if not member:
            raise MemberNotExistsException()
        if not user.is_superuser and user.person_id != member.person_id:
            raise VancedHTTPException(
                status_code=403, detail=ErrorCode.NOT_MEMBER_PERSON
            )
    return member, user
