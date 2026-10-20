from logging import getLogger
from profile.api.v1.access import ensure_self_or_superuser
from profile.api.v1.schema.contact import (
    ContactCreate,
    ContactItemCreate,
    ContactItemPutData,
    ContactItemRead,
    ContactPatch,
    ContactPatchData,
    ContactPut,
    ContactPutData,
    ContactRead,
)
from profile.dependency.account import CallerPersonDep, RequiredPersonDep
from profile.dependency.contact import ContactUOWDep, PersonContactUOWDep
from profile.filter.contact import ContactFilter
from profile.service.contact import ContactService
from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep, UserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/contacts", tags=["contact"])

logger = getLogger(__name__)


@router.get(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def get_my_contacts(
    user: ActiveUserJWTDep,
    person_id: RequiredPersonDep,
    uow: ContactUOWDep,
    filter: ContactFilter = FilterDepends(ContactFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[ContactItemRead]:
    return PageV1[ContactItemRead].from_dto(
        await ContactService(uow).search_by_person(
            person_id, filter.to_dto(), page_params.to_dto()
        )
    )


@router.post(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def create_my_contact(
    user: UserJWTDep,
    person_id: RequiredPersonDep,
    contact_data: ContactItemCreate,
    uow: PersonContactUOWDep,
) -> ContactRead:
    return ContactRead.from_dto(
        await ContactService(uow).create(
            ContactCreate(person_id=person_id, **contact_data.model_dump()).to_dto()
        )
    )


@router.put(
    "/my/{contact_id}",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def put_my_contact(
    contact_id: UUID,
    contact_data: ContactItemPutData,
    user: UserJWTDep,
    person_id: RequiredPersonDep,
    uow: ContactUOWDep,
) -> ContactRead:
    contact = ContactPut.model_validate(
        {"id": contact_id, "person_id": person_id, **contact_data.model_dump()}
    )
    return ContactRead.from_dto(await ContactService(uow).put(contact.to_dto()))


@router.patch(
    "/my/{contact_id}",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def patch_my_contact(
    contact_id: UUID,
    contact_data: ContactPatchData,
    user: UserJWTDep,
    person_id: RequiredPersonDep,
    uow: ContactUOWDep,
) -> ContactRead:
    await (service := ContactService(uow)).check_ownership(contact_id, person_id)
    contact = ContactPatch.model_validate(
        {"id": contact_id, **contact_data.model_dump()}
    )
    return ContactRead.from_dto(await service.patch(contact.to_dto()))


@router.delete(
    "/my/{contact_id}",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def delete_my_contact(
    contact_id: UUID, user: UserJWTDep, person_id: RequiredPersonDep, uow: ContactUOWDep
) -> None:
    await (service := ContactService(uow)).check_ownership(contact_id, person_id)
    await service.delete(contact_id)


@router.get("", responses={**auth_responses()})
async def get_contacts(
    user: SuperUserJWTDep,
    uow: ContactUOWDep,
    filter: ContactFilter = FilterDepends(ContactFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[ContactItemRead]:
    return PageV1[ContactItemRead].from_dto(
        await ContactService(uow).search(filter.to_dto(), page_params.to_dto())
    )


@router.get(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("contact")}
)
async def get_contact(
    uow: ContactUOWDep,
    user: UserJWTDep,
    caller: CallerPersonDep,
    id: UUID,
) -> ContactRead:
    contact = await ContactService(uow).read(id)
    ensure_self_or_superuser(user, contact.person_id, caller)
    return ContactRead.from_dto(contact)


@router.post(
    "", responses={**auth_responses(), **entity_not_found_responses("contact")}
)
async def create_contact(
    uow: PersonContactUOWDep,
    user: UserJWTDep,
    caller: CallerPersonDep,
    contact_data: ContactCreate,
) -> ContactRead:
    ensure_self_or_superuser(user, contact_data.person_id, caller)
    return ContactRead.from_dto(await ContactService(uow).create(contact_data.to_dto()))


@router.put(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("contact")}
)
async def put_contact(
    id: UUID,
    contact: ContactPutData,
    user: SuperUserJWTDep,
    uow: ContactUOWDep,
) -> ContactRead:
    return ContactRead.from_dto(
        await ContactService(uow).put(
            ContactPut.model_validate({"id": id, **contact.model_dump()}).to_dto()
        )
    )


@router.patch(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("contact")}
)
async def patch_contact(
    id: UUID,
    contact: ContactPatchData,
    user: SuperUserJWTDep,
    uow: ContactUOWDep,
) -> ContactRead:
    return ContactRead.from_dto(
        await ContactService(uow).patch(
            ContactPatch.model_validate({"id": id, **contact.model_dump()}).to_dto()
        )
    )


@router.delete(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("contact")}
)
async def delete_contact(id: UUID, user: SuperUserJWTDep, uow: ContactUOWDep) -> None:
    await ContactService(uow).delete(id)
