from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import auth_responses
from notify.api.v1.schema.preference import PreferencesRead, PreferencesUpdate
from notify.dependency.preference import PreferenceUOWDep
from notify.service.preference import PreferenceService

router = APIRouter(prefix="/preferences", tags=["notify"])


@router.get("/my", responses={**auth_responses()})
async def get_my_preferences(
    user: ActiveUserJWTDep,
    uow: PreferenceUOWDep,
) -> PreferencesRead:
    return PreferencesRead.from_dto(await PreferenceService(uow).get_my(user.id))


@router.put("/my", responses={**auth_responses()})
async def set_my_preferences(
    data: PreferencesUpdate,
    user: ActiveUserJWTDep,
    uow: PreferenceUOWDep,
) -> PreferencesRead:
    """Full replace of preferences. Email is forced on (guaranteed transport)."""
    return PreferencesRead.from_dto(
        await PreferenceService(uow).set_my(user.id, data.to_dto())
    )
