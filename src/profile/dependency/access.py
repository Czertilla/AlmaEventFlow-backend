from profile.access import PersonalDataPolicy
from profile.dependency.account import CallerPersonDep
from profile.service.access_data import AccessDataService
from profile.uow.access import AccessUOW
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from core.dependencies.auth import UserJWTDep
from core.schema.user import UserJWT

from ._uow import UOWDep

AccessUOWDep = Annotated[AccessUOW, Depends(UOWDep(AccessUOW))]


async def get_policy(
    user: UserJWTDep, caller_person_id: CallerPersonDep, uow: AccessUOWDep
) -> PersonalDataPolicy:
    return build_policy(user, caller_person_id, uow)


def build_policy(
    user: UserJWT, caller_person_id: UUID | None, uow: AccessUOW
) -> PersonalDataPolicy:
    return PersonalDataPolicy(user, caller_person_id, AccessDataService(uow))


PolicyDep = Annotated[PersonalDataPolicy, Depends(get_policy)]
