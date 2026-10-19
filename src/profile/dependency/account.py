from profile.dependency.person import PersonUOWDep
from profile.exc.user import NonPersonalUserException
from profile.service.account import PersonAccountService
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from core.dependencies.auth import ActiveUserJWTDep


async def get_caller_person(user: ActiveUserJWTDep, uow: PersonUOWDep) -> UUID | None:
    return await PersonAccountService(uow).resolve(user)


CallerPersonDep = Annotated[UUID | None, Depends(get_caller_person)]


async def get_required_caller_person(person_id: CallerPersonDep) -> UUID:
    if person_id is None:
        raise NonPersonalUserException()
    return person_id


RequiredPersonDep = Annotated[UUID, Depends(get_required_caller_person)]
