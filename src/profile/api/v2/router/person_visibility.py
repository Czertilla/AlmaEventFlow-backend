from profile.api.v2.docs import VISIBILITY_ERRORS
from profile.api.v2.schema.visibility import (
    VisibilityEntryRead,
    VisibilityRead,
    VisibilitySetData,
)
from profile.dependency.visibility import VisibilityUOWDep
from profile.service.visibility_settings import ADMIN, VisibilitySettingsService
from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import SuperUserJWTDep
from core.schema.error import auth_responses

router = APIRouter(
    prefix="/persons/{person_id}/visibility", tags=["visibility", "person"]
)


@router.get("", responses={**auth_responses()})
async def get_person_visibility(
    person_id: UUID, user: SuperUserJWTDep, uow: VisibilityUOWDep
) -> VisibilityRead:
    entries = await VisibilitySettingsService(uow).entries(person_id)
    return VisibilityRead(items=[VisibilityEntryRead.from_dto(e) for e in entries])


@router.put("/{field_key}", responses={**auth_responses(), **VISIBILITY_ERRORS})
async def set_person_visibility(
    person_id: UUID,
    field_key: str,
    data: VisibilitySetData,
    user: SuperUserJWTDep,
    uow: VisibilityUOWDep,
) -> VisibilityEntryRead:
    """An administrator sets the audience; the change is kept with `source=admin`."""
    entry = await VisibilitySettingsService(uow).set(
        person_id, field_key, data.to_dto(), actor_user_id=user.id, source=ADMIN
    )
    return VisibilityEntryRead.from_dto(entry)


@router.delete("/{field_key}", responses={**auth_responses(), **VISIBILITY_ERRORS})
async def reset_person_visibility(
    person_id: UUID, field_key: str, user: SuperUserJWTDep, uow: VisibilityUOWDep
) -> VisibilityEntryRead:
    entry = await VisibilitySettingsService(uow).reset(
        person_id, field_key, actor_user_id=user.id, source=ADMIN
    )
    return VisibilityEntryRead.from_dto(entry)
