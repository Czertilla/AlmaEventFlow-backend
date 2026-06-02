from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from profile.dependency.contact import ContactUOWDep, PersonContactUOWDep
from profile.exc.user import NonPersonalUserException
from profile.filter.contact import ContactFilter
from profile.schema.contact import (
    ContactCreate,
    ContactItemCreate,
    ContactItemRead,
    ContactPatch,
    ContactPatchData,
    ContactPut,
    ContactPutData,
    ContactRead,
)
from profile.service.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["contact"])

logger = getLogger(__name__)


@router.get("/my")
async def get_my_contacts(
    user: ActiveUserJWTDep,
    uow: ContactUOWDep,
    filter: ContactFilter = FilterDepends(ContactFilter),
    page_params=Depends(SPageParam),
) -> SPage[ContactItemRead]:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await ContactService(uow).search_by_person(
        user.person_id, filter, page_params
    )


@router.post("/my")
async def create_my_contact(
    user: UserJWTDep,
    contact_data: ContactItemCreate,
    uow: PersonContactUOWDep,
) -> ContactRead:
    if (person_id := user.person_id) is None:
        raise NonPersonalUserException()
    return await ContactService(uow).create(
        ContactCreate(person_id=person_id, **contact_data.model_dump())
    )


@router.put("/my/{contact_id}")
async def put_my_contact(
    contact_id: UUID,
    contact_data: ContactPutData,
    user: UserJWTDep,
    uow: ContactUOWDep,
) -> ContactRead:
    if (person_id := user.person_id) is None:
        raise NonPersonalUserException()
    contact = ContactPut(
        id=contact_id, person_id=person_id, **contact_data.model_dump()
    )
    return await ContactService(uow).put(contact)


@router.patch("/my/{contact_id}")
async def patch_my_contact(
    contact_id: UUID,
    contact_data: ContactPatchData,
    user: UserJWTDep,
    uow: ContactUOWDep,
) -> ContactRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := ContactService(uow)).check_ownership(
        contact_id, user.person_id
    )
    contact = ContactPatch(id=contact_id, **contact_data.model_dump())
    return await service.patch(contact)


@router.delete("/my/{contact_id}")
async def delete_my_contact(
    contact_id: UUID, user: UserJWTDep, uow: ContactUOWDep
) -> None:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := ContactService(uow)).check_ownership(
        contact_id, user.person_id
    )
    await service.delete(contact_id)


@router.get("/{id}")
async def get_contact(
    uow: ContactUOWDep,
    user: UserJWTDep,
    id: UUID,
) -> ContactRead:
    return await ContactService(uow).read(id)


@router.post("/{id}")
async def create_contact(
    uow: ContactUOWDep,
    user: UserJWTDep,
    contact_data=Depends(ContactCreate),
) -> ContactRead:
    return await ContactService(uow).create(contact_data)


@router.put("/{id}")
async def put_contact(
    user: SuperUserJWTDep,
    uow: ContactUOWDep,
    contact=Depends(ContactPut),
) -> ContactRead:
    return await ContactService(uow).put(contact)


@router.patch("/{id}")
async def patch_contact(
    user: SuperUserJWTDep,
    uow: ContactUOWDep,
    contact=Depends(ContactPatch),
) -> ContactRead:
    return await ContactService(uow).patch(contact)


@router.delete("/{id}")
async def delete_contact(
    id: UUID, user: SuperUserJWTDep, uow: ContactUOWDep
) -> None:
    await ContactService(uow).delete(id)
