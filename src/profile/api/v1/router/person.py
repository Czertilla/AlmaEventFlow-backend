from logging import getLogger
from profile.api.v1.access import ensure_self_or_superuser
from profile.api.v1.schema.contact import (
    ContactCreate,
    ContactItemCreate,
    ContactItemRead,
    ContactRead,
)
from profile.api.v1.schema.person import (
    PersonCreate,
    PersonItemRead,
    PersonPatch,
    PersonPatchData,
    PersonPut,
    PersonPutData,
    PersonRead,
)
from profile.dependency.contact import ContactUOWDep, PersonContactUOWDep
from profile.dependency.person import PersonUOWDep
from profile.exc.user import NonPersonalUserException
from profile.filter.contact import ContactFilter
from profile.filter.person import PersonFilter
from profile.service.contact import ContactService
from profile.service.person import PersonService
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep, UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/persons", tags=["person"])


logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def search_person(
    uow: PersonUOWDep,
    user: UserJWTDep,
    filter: PersonFilter = FilterDepends(PersonFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[PersonItemRead]:
    return PageV1[PersonItemRead].from_dto(
        await PersonService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def get_my_person(user: ActiveUserJWTDep, uow: PersonUOWDep) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return PersonRead.from_dto(await PersonService(uow).read(user.person_id))


@router.put(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def put_my_person(
    person_data: PersonPutData, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return PersonRead.from_dto(
        await PersonService(uow).put(
            PersonPut(id=user.person_id, **person_data.model_dump()).to_dto()
        )
    )


@router.patch(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def patch_my_person(
    person_data: PersonPatchData, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return PersonRead.from_dto(
        await PersonService(uow).patch(
            PersonPatch(id=user.person_id, **person_data.model_dump()).to_dto()
        )
    )


@router.get(
    "/{person_id}",
    responses={**auth_responses(), **entity_not_found_responses("person")},
)
async def get_person(person_id: UUID, uow: PersonUOWDep) -> PersonRead:
    return PersonRead.from_dto(await PersonService(uow).read(person_id))


@router.post("", responses={**auth_responses()})
async def create_person(
    person: PersonCreate, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    return PersonRead.from_dto(await PersonService(uow).create(person.to_dto()))


@router.put(
    "/{person_id}",
    responses={**auth_responses(), **entity_not_found_responses("person")},
)
async def put_person(
    person_id: UUID,
    person: PersonPutData,
    user: SuperUserJWTDep,
    uow: PersonUOWDep,
) -> PersonRead:
    return PersonRead.from_dto(
        await PersonService(uow).put(
            PersonPut(id=person_id, **person.model_dump()).to_dto()
        )
    )


@router.patch(
    "/{person_id}",
    responses={**auth_responses(), **entity_not_found_responses("person")},
)
async def patch_person(
    person_id: UUID,
    person: PersonPatchData,
    user: SuperUserJWTDep,
    uow: PersonUOWDep,
) -> PersonRead:
    return PersonRead.from_dto(
        await PersonService(uow).patch(
            PersonPatch(id=person_id, **person.model_dump()).to_dto()
        )
    )


@router.delete(
    "/{person_id}",
    responses={**auth_responses(), **entity_not_found_responses("person")},
)
async def delete_person(
    person_id: UUID, user: SuperUserJWTDep, uow: PersonUOWDep
) -> None:
    await PersonService(uow).delete(person_id)


contact_router = APIRouter(prefix="/{person_id}/contacts", tags=["person", "contact"])


@contact_router.get("", responses={**auth_responses()})
async def get_person_contacts(
    person_id: UUID,
    user: UserJWTDep,
    uow: ContactUOWDep,
    filter: ContactFilter = FilterDepends(ContactFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[ContactItemRead]:
    ensure_self_or_superuser(user, person_id)
    return PageV1[ContactItemRead].from_dto(
        await ContactService(uow).search_by_person(
            person_id, filter.to_dto(), page_params.to_dto()
        )
    )


@contact_router.post("", responses={**auth_responses()})
async def create_person_contact(
    person_id: UUID,
    contact: ContactItemCreate,
    user: SuperUserJWTDep,
    uow: PersonContactUOWDep,
) -> ContactRead:
    return ContactRead.from_dto(
        await ContactService(uow).create(
            ContactCreate(person_id=person_id, **contact.model_dump()).to_dto()
        )
    )


router.include_router(contact_router)
