from logging import getLogger
from uuid import UUID

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from profile.exc.contact import (
    ContactNotExistsException,
    ContactOwnershipException,
)
from profile.exc.person import PersonNotExistsException
from profile.filter.contact import ContactFilter
from profile.models.contact import ContactORM
from profile.schema.contact import (
    ContactCreate,
    ContactItemRead,
    ContactPatch,
    ContactPut,
    ContactRead,
)
from profile.uow.contact import ContactUOW
from profile.uow.person import PersonContactUOW


logger = getLogger(__name__)


class ContactService(BaseService[ContactUOW | PersonContactUOW]):
    @required_transaction
    async def _create(self, contact_create: ContactCreate) -> ContactORM:
        if not await self.uow.persons.exists_id(contact_create):
            raise PersonNotExistsException()
        return await self.uow.contacts.add_n_return(contact_create.model_dump())

    @required_transaction
    async def _read(self, contact_id: UUID) -> ContactORM | None:
        contact = await self.uow.contacts.get_by_id(contact_id)
        if contact is None:
            raise ContactNotExistsException()
        return contact

    @required_transaction
    async def _update(
        self, contact_id: UUID, contact_data: dict, *, flush: bool = False
    ) -> ContactORM:
        contact = await self.uow.contacts.update_one(
            contact_id, contact_data, flush
        )
        if contact is None:
            raise ContactNotExistsException()
        return contact

    @required_transaction
    async def _check_ownership(self, contact_id: UUID, person_id: UUID):
        exists = await self.uow.contacts.get_by_id(contact_id)
        if exists and exists.person_id != person_id:
            raise ContactOwnershipException()

    @required_transaction
    async def _upsert(self, contact_put: ContactPut) -> ContactORM:
        await self._check_ownership(contact_put.id, contact_put.person_id)
        return await self.uow.contacts.upsert(contact_put.model_dump())

    async def create(self, contact_create: ContactCreate) -> ContactRead:
        async with self.uow as uow:
            result = ContactRead.model_validate(
                await self._create(contact_create)
            )
            await uow.commit()
        return result

    async def read(self, contact_id: UUID) -> ContactRead:
        async with self.uow:
            return ContactRead.model_validate(await self._read(contact_id))

    async def search_by_person(
        self,
        person_id: UUID,
        filter: ContactFilter,
        page_params: SPageParam = SPageParam(),
    ) -> SPage[ContactItemRead]:
        async with self.uow as uow:
            contacts, total = await uow.contacts.search(
                filter,
                page_params,
                scope=[ContactORM.person_id == person_id],
            )
            return SPage(
                items=[
                    ContactItemRead.model_validate(contact)
                    for contact in contacts
                ],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, contact_patch: ContactPatch) -> ContactRead:
        async with self.uow as uow:
            contact_data = contact_patch.model_dump()
            result = ContactRead.model_validate(
                await self._update(contact_data.pop("id"), contact_data)
            )
            await uow.commit()
        return result

    async def put(self, contact_put: ContactPut) -> ContactRead:
        async with self.uow as uow:
            result = ContactRead.model_validate(await self._upsert(contact_put))
            await uow.commit()
        return result

    async def delete(self, contact_id: UUID) -> None:
        async with self.uow as uow:
            await self.uow.contacts.delete_one(contact_id)
            await uow.commit()

    async def check_ownership(self, contact_id: UUID, profile_id: UUID) -> None:
        async with self.uow:
            await self._check_ownership(contact_id, profile_id)
