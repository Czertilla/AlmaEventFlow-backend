from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from logging import getLogger

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from profile.dependency.contact import ContactUOWDep, PersonContactUOWDep
from profile.exc.user import NonPersonalUserException
from profile.dependency.person import PersonUOWDep
from profile.schema.contact import (
    ContactCreate,
    ContactItemCreate,
    ContactItemRead,
    ContactRead,
)
from profile.schema.person import (
    PersonCreate,
    PersonItemRead,
    PersonPatch,
    PersonPatchData,
    PersonPut,
    PersonPutData,
    PersonRead,
)
from profile.service.contact import ContactService
from profile.service.person import PersonService

router = APIRouter(prefix="/persons", tags=["person"])


logger = getLogger(__name__)


@router.get("")
async def get_many(
    uow: PersonUOWDep,
    user: UserJWTDep,
    page_param=Depends(SPageParam),
) -> SPage[PersonItemRead]:
    return await PersonService(uow).read_many(page_param)


@router.get("/my")
async def get_my_person(
    user: ActiveUserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await PersonService(uow).read(user.person_id)


@router.put("/my")
async def put_my_person(
    person_data: PersonPutData, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await PersonService(uow).put(
        PersonPut(id=user.person_id, **person_data.model_dump())
    )


@router.patch("/my")
async def patch_my_person(
    person_data: PersonPatchData, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await PersonService(uow).patch(
        PersonPatch(id=user.person_id, **person_data.model_dump())
    )


@router.get("/{person_id}")
async def get_person(
    person_id: UUID, user: ActiveUserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    return await PersonService(uow).read(person_id)


@router.post("/new")
async def create_person(
    person: PersonCreate, user: UserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    return await PersonService(uow).create(person)


@router.put("/{person_id}")
async def put_person(
    person: PersonPut, user: SuperUserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    return await PersonService(uow).put(person)


@router.patch("/{person_id}")
async def patch_person(
    person: PersonPatch, user: SuperUserJWTDep, uow: PersonUOWDep
) -> PersonRead:
    return await PersonService(uow).patch(person)


@router.delete("/{person_id}")
async def delete_person(
    person_id: UUID, user: SuperUserJWTDep, uow: PersonUOWDep
) -> None:
    await PersonService(uow).delete(person_id)


contact_router = APIRouter(
prefix="/{person_id}/contacts", tags=["person", "contact"]
)


@contact_router.get("")
async def get_person_contacts(
    person_id: UUID,
    user: UserJWTDep,
    uow: ContactUOWDep,
    page_params=Depends(SPageParam),
) -> SPage[ContactItemRead]:
    return await ContactService(uow).read_many_by_person(person_id, page_params)


@contact_router.post("")
async def create_person_contact(
    person_id: UUID,
    contact: ContactItemCreate,
    user: SuperUserJWTDep,
    uow: PersonContactUOWDep,
) -> ContactRead:
    return await ContactService(uow).create(
        ContactCreate(person_id=person_id, **contact.model_dump())
    )


router.include_router(contact_router)
