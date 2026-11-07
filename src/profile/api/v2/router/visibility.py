from profile.api.v2.docs import VISIBILITY_ERRORS
from profile.api.v2.schema.visibility import (
    VisibilityEntryRead,
    VisibilityRead,
    VisibilitySetData,
)
from profile.dependency.account import CallerPersonDep, RequiredPersonDep
from profile.dependency.visibility import VisibilityUOWDep
from profile.service.visibility_settings import OWNER, VisibilitySettingsService

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses

router = APIRouter(prefix="/visibility", tags=["visibility"])


@router.get("/my", responses={**auth_responses()})
async def get_my_visibility(
    user: UserJWTDep, person_id: CallerPersonDep, uow: VisibilityUOWDep
) -> VisibilityRead:
    """Who may see each personal field of the caller; the defaults without a person."""
    entries = await VisibilitySettingsService(uow).entries(person_id)
    return VisibilityRead(items=[VisibilityEntryRead.from_dto(e) for e in entries])


@router.put("/my/{field_key}", responses={**auth_responses(), **VISIBILITY_ERRORS})
async def set_my_visibility(
    field_key: str,
    data: VisibilitySetData,
    user: UserJWTDep,
    person_id: RequiredPersonDep,
    uow: VisibilityUOWDep,
) -> VisibilityEntryRead:
    """Sets the audience of a field. Narrowing is always allowed; widening is held
    back (`409 VISIBILITY_COOLDOWN`) for a while after the account link changed."""
    entry = await VisibilitySettingsService(uow).set(
        person_id, field_key, data.to_dto(), actor_user_id=user.id, source=OWNER
    )
    return VisibilityEntryRead.from_dto(entry)


@router.delete("/my/{field_key}", responses={**auth_responses(), **VISIBILITY_ERRORS})
async def reset_my_visibility(
    field_key: str,
    user: UserJWTDep,
    person_id: RequiredPersonDep,
    uow: VisibilityUOWDep,
) -> VisibilityEntryRead:
    """Returns the field to its default audience."""
    entry = await VisibilitySettingsService(uow).reset(
        person_id, field_key, actor_user_id=user.id, source=OWNER
    )
    return VisibilityEntryRead.from_dto(entry)
