from profile.api.v1.schema.person import PersonCreate, PersonRead
from profile.dependency.person import PersonUOWDep
from profile.exc.user import AccountAlreadyLinkedException
from profile.service.person import PersonService

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import ErrorCode, auth_responses, detail_400

router = APIRouter(prefix="/persons", tags=["person"])


@router.post(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ACCOUNT_ALREADY_LINKED)},
)
async def create_my_person(
    person: PersonCreate, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    """Creates the caller's own person and attaches it to the account.

    The access token carries the person id: refresh it afterwards, or the
    `/my` endpoints keep answering `ATTACHED_PERSON_REQUIRED`.
    """
    if user.person_id is not None:
        raise AccountAlreadyLinkedException()
    return PersonRead.from_dto(
        await PersonService(uow).create_own(user.id, person.to_dto())
    )
