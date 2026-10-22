from fastapi import APIRouter, Depends, status

from core.dependencies.auth import UserJWTDep
from core.schema.error import ErrorCode, auth_responses, error_response
from user.api.v2.schema.settings import UserSettingsPatch, UserSettingsRead
from user.dependency.user import get_settings_service
from user.service.settings import MAX_SETTINGS_BYTES, SettingsService

router = APIRouter(prefix="/users/me/settings", tags=["settings"])


@router.get("", responses={**auth_responses()})
async def read_my_settings(
    user: UserJWTDep,
    service: SettingsService = Depends(get_settings_service),
) -> UserSettingsRead:
    """The caller's client settings, the same on every device and session."""
    return UserSettingsRead.from_dto(await service.read(user.id))


@router.patch(
    "",
    responses={
        **auth_responses(),
        **error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"The settings together would be over {MAX_SETTINGS_BYTES} bytes",
            {ErrorCode.SETTINGS_TOO_LARGE: {}},
        ),
    },
)
async def patch_my_settings(
    body: UserSettingsPatch,
    user: UserJWTDep,
    service: SettingsService = Depends(get_settings_service),
) -> UserSettingsRead:
    """Changes only the named settings and returns all of them.

    A device that sends just what the person changed never overwrites what
    another device changed meanwhile. A request that changes nothing leaves the
    revision as it was.
    """
    return UserSettingsRead.from_dto(await service.patch(user.id, body.to_dto()))
