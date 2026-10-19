from profile.api.v2.schema.profile import MyProfileRead, MyProfileWrite
from profile.dependency.account import CallerPersonDep
from profile.dependency.my_profile import MyProfileUOWDep
from profile.exc.profile import ProfileNotExistsException
from profile.service.my_profile import MyProfileService

from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep, UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_403,
    entity_not_found_responses,
    error_response,
)

router = APIRouter(prefix="/profiles", tags=["profile"])


@router.get(
    "/my",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def get_my_profile(
    user: ActiveUserJWTDep, person_id: CallerPersonDep, uow: MyProfileUOWDep
) -> MyProfileRead:
    """The caller's whole profile: name, birthdate, diet, student card, contacts.

    `404 PROFILE_NOT_FOUND` until the user has made one.
    """
    if person_id is None:
        raise ProfileNotExistsException()
    return MyProfileRead.from_dto(await MyProfileService(uow).read(person_id))


@router.post(
    "/my",
    responses={
        **auth_responses(),
        **detail_403(ErrorCode.PROFILE_ALREADY_EXISTS),
        **error_response(
            409,
            "The account claims a person that the profile service has no link for",
            {ErrorCode.ACCOUNT_LINK_OUT_OF_SYNC: {}},
        ),
    },
)
async def create_my_profile(
    profile: MyProfileWrite, user: UserJWTDep, uow: MyProfileUOWDep
) -> MyProfileRead:
    """Makes the caller's profile in one transaction and links it to the account.

    A user makes one profile for themselves: a second attempt is
    `403 PROFILE_ALREADY_EXISTS`. The access token carries the linked person
    only after its next refresh; profile endpoints do not depend on it.
    """
    return MyProfileRead.from_dto(
        await MyProfileService(uow).create(
            user.id, profile.to_dto(), claimed_person_id=user.person_id
        )
    )


@router.put(
    "/my",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def put_my_profile(
    profile: MyProfileWrite,
    user: UserJWTDep,
    person_id: CallerPersonDep,
    uow: MyProfileUOWDep,
) -> MyProfileRead:
    """Replaces the whole profile: a student card or a contact left out is removed."""
    if person_id is None:
        raise ProfileNotExistsException()
    return MyProfileRead.from_dto(
        await MyProfileService(uow).replace(person_id, profile.to_dto())
    )
